#!/usr/bin/env python3
"""Retrieve completed-run evidence using the authenticated gh session; never read secret values."""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('run_id', type=int)
p.add_argument('--repo',default='arpit175ak/metlifeimagescan')
a=p.parse_args()
root=Path('results')
root.mkdir(exist_ok=True)
def gh(*args):
    return subprocess.check_output(['gh',*args],text=True)
run=json.loads(gh('api',f'repos/{a.repo}/actions/runs/{a.run_id}'))
if run['status']!='completed':
    raise SystemExit('Run is not completed; no final timing can be reported yet')
jobs=json.loads(gh('api',f'repos/{a.repo}/actions/runs/{a.run_id}/jobs?per_page=100'))
with tempfile.TemporaryDirectory(prefix='metlife-artifacts-') as d:
    subprocess.run(['gh','run','download',str(a.run_id),'--repo',a.repo,'--dir',d],check=True)
    for src in Path(d).rglob('*'):
        if src.is_file() and src.name in {'docker-events.jsonl','scanner-version.txt','build.json','runner.json','image-metadata.json','image-inspect.json','image-inspect-after.json','action-reference.txt','results-vuln.json'}:
            shutil.copy2(src,root/src.name)
(root/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')
(root/'run.json').write_text(json.dumps(run,indent=2)+'\n')
log=gh('run','view',str(a.run_id),'--repo',a.repo,'--log')
# Keep only known status events. Do not persist arbitrary log bodies/tenant endpoints.
markers={
 'setup_start':'Downloading AccuKnox ASPM Scanner...',
 'scan_start':'Running AccuKnox vulnerability scan...',
 'upload_start':' - INFO - Uploading scan results from ',
 'upload_success':'Scan results uploaded successfully!',
 'findings':' - ERROR - Vulnerabilities matching severities:',
 'scan_failure':' - ERROR - Scan failed.',
}
events={}
for line in log.splitlines():
    if '\x1b[36' in line: # rendered shell source, rather than a runtime event
        continue
    match=re.search(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z) ',line)
    if not match:
        continue
    for name, marker in markers.items():
        if marker in line:
            events.setdefault(name,match.group(1))

def delta(start,end):
    return (dt.datetime.fromisoformat(events[end].replace('Z','+00:00'))-dt.datetime.fromisoformat(events[start].replace('Z','+00:00'))).total_seconds()
metrics={}
if {'setup_start','scan_start'}<=events.keys():
    metrics['Scanner setup/initialization duration']=f"{delta('setup_start','scan_start'):.3f} s (CLI download and tool install only; scanner-container pull/database work follows)"
if {'upload_start','upload_success'}<=events.keys():
    metrics['Results upload duration']=f"{delta('upload_start','upload_success'):.3f} s (client log interval; includes HTTP request/response)"
    metrics['Console upload status']='Scanner confirmed successful HTTP upload; tenant UI ingestion/display not independently verified'
if 'upload_success' in events and 'findings' in events and 'scan_failure' not in events:
    metrics['Scan status']='Completed with vulnerability findings; soft_fail accepted findings; successful HTTP console upload confirmed'
# Prove that the expected binaries were requested in execution, not just in shell source.
if 'releases/download/v0.14.0/accuknox-aspm-scanner' in log:
    metrics['Scanner version']='ASPM CLI v0.14.0 (download URL); container engine image aquasec/trivy:0.65.0 (configured version; binary --version not independently queried)'
(root/'verified-evidence.json').write_text(json.dumps({'run_id':a.run_id,'utc_events':events,'metrics':metrics},indent=2)+'\n')
subprocess.run(['python3','scripts/benchmark-summary.py'],check=True)
