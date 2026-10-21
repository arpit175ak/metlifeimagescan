#!/usr/bin/env python3
"""Launch bounded independent Actions runs and summarize completed batch evidence."""
import argparse
import concurrent.futures
import datetime as dt
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import tempfile

REPO='arpit175ak/metlifeimagescan'
ACTION='AccuKnox official action (build, setup, scan, upload)'
def gh(*args):
    return subprocess.check_output(['gh',*args],text=True)
def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()
def epoch(s):
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
p=argparse.ArgumentParser()
sub=p.add_subparsers(dest='command',required=True)
l=sub.add_parser('launch'); l.add_argument('--count',type=int,choices=[1,5,10],required=True); l.add_argument('--fixture-run-id',type=int,required=True); l.add_argument('--batch',required=True)
c=sub.add_parser('collect'); c.add_argument('--batch',required=True)
a=p.parse_args()
if not re.fullmatch(r'[a-zA-Z0-9_-]+',a.batch):
    raise SystemExit('Batch must be an alphanumeric identifier with optional hyphens/underscores')
root=Path('results')/a.batch; root.mkdir(parents=True,exist_ok=True)
manifest=root/'batch.json'
if a.command=='launch':
    if manifest.exists():
        raise SystemExit('Batch already exists; use collect or a new identifier')
    fixture=json.loads(gh('api',f'repos/{REPO}/actions/runs/{a.fixture_run_id}'))
    if fixture['conclusion']!='success':
        raise SystemExit('Shared fixture run must be successful')
    data={'batch':a.batch,'requested_concurrency':a.count,'fixture_run_id':a.fixture_run_id,'dispatch_started_at':utc(),'runs':[]}
    for i in range(1,a.count+1):
        output=gh('workflow','run','container-scan.yml','--repo',REPO,'--ref','main','-f',f'fixture_run_id={a.fixture_run_id}','-f',f'batch_id={a.batch}','-f',f'sample={i}')
        match=re.search(r'/actions/runs/(\d+)',output)
        if not match:
            manifest.write_text(json.dumps(data,indent=2)+'\n')
            raise SystemExit('Dispatch returned no run URL; inspect Actions before retrying')
        data['runs'].append({'sample':i,'run_id':int(match.group(1))})
        manifest.write_text(json.dumps(data,indent=2)+'\n')
        print(f"Dispatched {i}/{a.count}: {match.group(1)}",flush=True)
    data['dispatch_completed_at']=utc(); manifest.write_text(json.dumps(data,indent=2)+'\n')
    raise SystemExit(0)

data=json.loads(manifest.read_text())
def collect(item):
    rid=item['run_id']; out=root/str(rid); out.mkdir(exist_ok=True)
    run=json.loads(gh('api',f'repos/{REPO}/actions/runs/{rid}'))
    if run['status']!='completed':
        return {**item,'status':run['status']}
    jobs=json.loads(gh('api',f'repos/{REPO}/actions/runs/{rid}/jobs'))
    job=next(j for j in jobs['jobs'] if j['name']=='baseline')
    scan=next((s for s in job['steps'] if s['name']==ACTION),{})
    log=gh('run','view',str(rid),'--repo',REPO,'--log')
    with tempfile.TemporaryDirectory(prefix='metlife-sample-') as tmp:
        subprocess.run(['gh','run','download',str(rid),'--repo',REPO,'--name',f'metlife-benchmark-{rid}-1','--dir',tmp],check=True,stdout=subprocess.DEVNULL)
        measurements={}
        for name in ['runner.json','image-metadata.json','image-load.json','docker-events.jsonl','findings-count.json','build.json']:
            source=Path(tmp)/'results'/name
            if not source.exists():
                source=Path(tmp)/name
            if source.exists():
                contents=source.read_text(); (out/name).write_text(contents)
                measurements[name]=[json.loads(x) for x in contents.splitlines()] if name.endswith('.jsonl') else json.loads(contents)
        report_path=Path(tmp)/'results-vuln.json'
        if report_path.exists():
            report=json.loads(report_path.read_text())
            report_evidence={'image_id':report.get('Metadata',{}).get('ImageID'),'scanner_reported_size':report.get('Metadata',{}).get('Size'),'records':sum(len(r.get('Vulnerabilities') or []) for r in report.get('Results',[])),'schema_version':report.get('SchemaVersion')}
            measurements['report-evidence.json']=report_evidence
            (out/'report-evidence.json').write_text(json.dumps(report_evidence,indent=2)+'\n')
    download=next((s for s in job['steps'] if s['name']=='Download immutable shared fixture'),{})
    download_seconds=epoch(download['completed_at'])-epoch(download['started_at']) if download.get('conclusion')=='success' else None
    docker_events=measurements.get('docker-events.jsonl',[])
    scanner_pull_seconds=sum(e['seconds'] for e in docker_events if e['kind']=='pull')
    scanner_invocation_seconds=sum(e['seconds'] for e in docker_events if e['kind']=='run')
    uploaded='Scan results uploaded successfully!' in log
    # Explicitly check the invocation image against the baseline artifact's measured image.
    image=measurements.get('image-metadata.json',{})
    findings=measurements.get('findings-count.json',{}).get('records')
    report_evidence=measurements.get('report-evidence.json',{})
    identity_matches=report_evidence.get('image_id')==image.get('image_id') and bool(image.get('image_id'))
    valid=identity_matches and report_evidence.get('records')==findings and run['conclusion']=='success' and scan.get('conclusion')=='success' and uploaded and isinstance(findings,int) and findings>0 and image.get('uncompressed_bytes',0)>1073741824
    row={**item,'url':run['html_url'],'status':run['status'],'run_conclusion':run['conclusion'],'verified_success':valid,'report_image_id_matches':identity_matches,'upload_http_success':uploaded,'findings_records':findings,'image_id':image.get('image_id'),'image_uncompressed_bytes':image.get('uncompressed_bytes'),'runner':measurements.get('runner.json'),'created_at':run['created_at'],'job_started_at':job['started_at'],'job_completed_at':job['completed_at'],'action_started_at':scan.get('started_at'),'action_completed_at':scan.get('completed_at'),'action_seconds':epoch(scan['completed_at'])-epoch(scan['started_at']) if scan.get('conclusion') not in {None,'skipped'} else None,'job_seconds':epoch(job['completed_at'])-epoch(job['started_at']),'queue_to_job_seconds':epoch(job['started_at'])-epoch(run['created_at']),'fixture_download_seconds':download_seconds,'fixture_load_seconds':measurements.get('image-load.json',{}).get('seconds'),'scanner_pull_seconds':scanner_pull_seconds,'scanner_invocation_seconds':scanner_invocation_seconds}
    (out/'sample.json').write_text(json.dumps(row,indent=2)+'\n')
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(collect,data['runs']))
(root/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
pending=[r for r in rows if r['status']!='completed']
if pending:
    print(f"Pending {len(pending)}/{len(rows)} samples: "+', '.join(str(r['run_id']) for r in pending)); raise SystemExit(2)
ids={r['image_id'] for r in rows if r.get('image_id')}
if len(ids)>1:
    raise SystemExit('Different image IDs detected; batch is not comparable')
successes=[r for r in rows if r['verified_success']]
latencies=[r['action_seconds'] for r in successes]
# Batch interval includes runner setup, fixture acquisition, action, artifact collection and cleanup.
start=min(epoch(r['job_started_at']) for r in rows); end=max(epoch(r['job_completed_at']) for r in rows)
dispatch_start=epoch(data['dispatch_started_at'])
# Actual official-action overlap (not merely job overlap or requested matrix size).
points=[]
for r in rows:
    if r.get('action_started_at') and r.get('action_completed_at') and r['action_seconds'] is not None:
        points.extend([(epoch(r['action_started_at']),1),(epoch(r['action_completed_at']),-1)])
active=peak=0
for _,change in sorted(points):
    active+=change;peak=max(peak,active)
summary={'fixture_run_id':data['fixture_run_id'],'requested_concurrency':data['requested_concurrency'],'samples':len(rows),'verified_successes':len(successes),'failed_or_unverified':len(rows)-len(successes),'image_id':next(iter(ids)) if ids else None,'batch_started_at':dt.datetime.fromtimestamp(start,dt.timezone.utc).isoformat(),'batch_completed_at':dt.datetime.fromtimestamp(end,dt.timezone.utc).isoformat(),'batch_seconds':end-start,'successful_scans_per_hour':len(successes)*3600/(end-start),'dispatch_to_last_job_seconds':end-dispatch_start,'dispatch_to_last_job_scans_per_hour':len(successes)*3600/(end-dispatch_start),'peak_action_overlap':peak,'mean_action_seconds':statistics.mean(latencies) if latencies else None,'p95_action_seconds_nearest_rank':sorted(latencies)[math.ceil(.95*len(latencies))-1] if len(latencies)>=5 else None,'p95_note':'Nearest-rank P95; n=5/10 is small and the estimate is not a stable production tail-latency estimate.','latency_scope':'Official action wall clock, including cached FROM build, setup, scanner pull, DB/network, analysis and uploads.','runner_specs':sorted({(r['runner']['cpu'],r['runner']['ram_bytes']) for r in rows if r.get('runner')})}
summary['phase_means_seconds']={key:statistics.mean(r[key] for r in rows if r.get(key) is not None) for key in ['fixture_download_seconds','fixture_load_seconds','scanner_pull_seconds','scanner_invocation_seconds','queue_to_job_seconds'] if any(r.get(key) is not None for r in rows)}
summary['queue_to_job_range_seconds']=[min(r['queue_to_job_seconds'] for r in rows),max(r['queue_to_job_seconds'] for r in rows)]
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
