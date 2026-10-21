#!/usr/bin/env python3
"""Summarize local artifacts; optionally enrich using completed GitHub jobs/run JSON."""
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path('results')
ROOT.mkdir(exist_ok=True)
NA = 'Not separately measurable'
def read(name, default=None):
    p = ROOT / name
    return json.loads(p.read_text()) if p.exists() else default

def seconds(a, b):
    return (dt.datetime.fromisoformat(b.replace('Z', '+00:00')) - dt.datetime.fromisoformat(a.replace('Z', '+00:00'))).total_seconds()

image = read('image-metadata.json', {})
build = read('build.json', {})
runner = read('runner.json', {})
metrics = {
    'CI/CD platform': 'GitHub Actions',
    'Image name': image.get('image', 'Pending execution'),
    'Image digest': image.get('image_id', 'Pending execution') + (' (local image configuration digest; not registry manifest digest)' if image else ''),
    'Image size': f"{image['uncompressed_bytes']:,} bytes ({image['uncompressed_bytes']/1e9:.3f} GB), Docker virtual/uncompressed size" if image else 'Pending build',
    'Compressed registry image size': 'Unavailable: benchmark image is local and is not pushed to a registry',
    'Image download size': NA,
    'Runner CPU/RAM': f"{runner['cpu']} logical CPUs / {runner['ram_bytes']/2**30:.2f} GiB RAM" if runner else 'Pending execution',
    'Scanner version': 'Pending runtime evidence',
    'Build duration': f"{build['seconds']:.3f} s (includes base-image acquisition and build export)" if build else 'Pending build',
    'Image pull duration': NA,
    'Scanner setup/initialization duration': NA,
    'Actual scanner analysis duration': NA,
    'AccuKnox action duration': 'Pending completed job metadata',
    'Results upload duration': NA,
    'Total CI/CD job duration': 'Pending completed job metadata',
    'Total workflow duration': 'Pending completed run metadata',
    'Vulnerability findings': 'Pending valid scan report',
    'Scan status': os.environ.get('SCAN_OUTCOME', 'Pending execution') + '; scanner completion and tenant upload require separate verification',
    'Console upload status': 'Pending explicit upload confirmation; a green action alone is insufficient',
    'Concurrent scans': '1 baseline job configured; concurrency testing pending successful baseline',
    'Measured throughput': 'Pending verified successful scans and completed batch timing',
}
events_path = ROOT / 'docker-events.jsonl'
if events_path.exists():
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line]
    pulls = [e for e in events if e['kind'] == 'pull']
    runs = [e for e in events if e['kind'] == 'run']
    if pulls:
        metrics['Scanner container pull duration'] = f"{sum(e['seconds'] for e in pulls):.3f} s (scanner tooling image, not benchmark image)"
    if runs:
        metrics['Scanner invocation wall duration'] = f"{sum(e['seconds'] for e in runs):.3f} s (container startup, DB/network, vulnerability and default secret analysis; not pure vulnerability analysis)"
report = Path('results-vuln.json')
if not report.exists():
    report = ROOT / 'results-vuln.json'
if report.exists():
    try:
        data = json.loads(report.read_text())
        if isinstance(data, dict) and isinstance(data.get('Results'), list) and data.get('SchemaVersion'):
            findings = [v for r in data['Results'] for v in (r.get('Vulnerabilities') or [])]
            metrics['Vulnerability findings'] = f"{len(findings)} package vulnerability records (not deduplicated CVEs)"
            (ROOT / 'findings-count.json').write_text(json.dumps({'records':len(findings)},indent=2)+'\n')
    except (ValueError, TypeError):
        metrics['Vulnerability findings'] = 'Invalid JSON report; scan success unverified'
jobs = read('jobs.json', {}).get('jobs', [])
for job in jobs:
    if job['name'] != 'baseline':
        continue
    if job.get('completed_at'):
        metrics['Total CI/CD job duration'] = f"{seconds(job['started_at'],job['completed_at']):.3f} s (includes runner job preparation and cleanup)"
    steps = job.get('steps', [])
    scan = next((s for s in steps if s['name'] == 'AccuKnox official action (build, setup, scan, upload)'), None)
    if scan and scan.get('completed_at'):
        metrics['AccuKnox action duration'] = f"{seconds(scan['started_at'],scan['completed_at']):.3f} s (includes internal build, setup, database/network, scan and uploads)"
        metrics['Scan status'] = scan['conclusion'] + '; verify report and console upload independently'
run = read('run.json', {})
if run.get('updated_at') and run.get('status') == 'completed':
    metrics['Total workflow duration'] = f"{seconds(run['created_at'],run['updated_at']):.3f} s (creation to terminal update; includes queueing)"
# Operator records only confirmations actually observed in completed logs/UI.
verified = read('verified-evidence.json', {})
for key, value in verified.get('metrics', {}).items():
    if key in metrics:
        metrics[key] = value
(ROOT / 'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
text = '# MetLife AccuKnox container benchmark\n\n'
if run.get('html_url'):
    text += f"Run: {run['html_url']}\n\n"
text += '| Metric | Actual result |\n|---|---|\n'
text += ''.join(f'| {k} | {str(v).replace(chr(10), " ").replace("|", "/")} |\n' for k,v in metrics.items())
text += '''
The image contains pinned Python 3.9.18 / Debian 11 packages and 1,152 MiB of deterministic, highly compressible test padding. Its uncompressed size is deliberately above 1 GiB. This is a padded size fixture, not a representative 1 GB of application dependencies, compressed registry content, or transferred data. Findings must come from the actual report.

The official action builds once. A transparent Docker wrapper measures that build and verifies its image ID and size before the scanner starts. The image ID is checked again afterward. No benchmark image registry pull occurs: the scanner uses the local tag. Base-layer downloads are inside the build timer; scanner tooling/database downloads are inside action time. Internal analysis and console-upload phases are unavailable unless explicit scanner evidence exposes them. `upload_results` controls GitHub artifacts, not console upload.

GitHub-hosted results do not validate MetLife production throughput. Sanjay's proposal is 3 nodes, each 8 vCPU / 32 GB RAM / 500 GB storage: total 24 vCPU / 96 GB / 1,500 GB. This is proposed sizing only. A local registry and on-premises scanner can reduce external internet dependency; registry speed, storage I/O, CPU, RAM, scanner implementation, vulnerability database availability, cache state and workload composition still affect performance.

Varendra: use only the measured values above. Before committing to hundreds of builds per hour across 2,000–3,000 repositories, 3,000+ images and approximately 150 hourly base images, validate representative 1–3.5 GB images, cold/warm caches, database updates, security gating, and sustained controlled concurrency on the proposed on-premises environment. SAST, SCA and Secrets require their own benchmarks. No production capacity claim is made by this container test.

Concurrency levels 5 and 10 are pending a confirmed successful baseline, immutable shared image distribution and a review of GitHub runner limits. Queued jobs do not count as concurrent execution. Throughput = verified successful scans / elapsed batch hours; P95 requires a stated sample size and method.
'''
(ROOT / 'benchmark-summary.md').write_text(text)
print(text)
