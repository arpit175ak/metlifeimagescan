# MetLife POC — AccuKnox container image scanning benchmark

Technical benchmarking owner: Varendra Maurya. Infrastructure coordination: Sanjay.

This repository runs an initial GitHub Actions technical validation. MetLife production is strictly on-premises; GitHub-hosted runner performance does not validate the proposed on-premises capacity.

## Run

Configure repository Actions secrets `ACCUKNOX_TOKEN`, `ACCUKNOX_LABEL`, and `ACCUKNOX_ENDPOINT` using the tenant's expected values. Never commit credentials. Push implementation changes to `main` or run:

```bash
gh workflow run container-scan.yml --repo arpit175ak/metlifeimagescan --ref main
gh run list --repo arpit175ak/metlifeimagescan --workflow container-scan.yml
```

The workflow builds exactly once inside `accuknox/container-scan-action@latest`, verifies a size above 1 GiB before scanning, scans all documented severities with `soft_fail: true`, and preserves reports and measurements for 30 days. SBOM is disabled. Failures still require inspection: soft fail and a green job do not prove a successful scan or console upload.

## Fixture and size

`Dockerfile` pins the Linux amd64 manifest for Python 3.9.18 on Debian bullseye. Public vulnerability references: [Python security history](https://www.python.org/downloads/security/) and [Debian security tracker](https://security-tracker.debian.org/tracker/). No arbitrary vulnerable binaries, malware, exploits, credentials or active attack tools are added. The old packages are candidates for findings; the report is authoritative.

The image adds 1,152 MiB of repeated non-sensitive text with fixed file timestamps. It is cheap to generate and highly compressible. This tests an image larger than 1 GB by Docker virtual/uncompressed bytes, **not** a 1 GB compressed download or 1 GB of dependencies. The scan workload is not representative of all equally sized real images. The base manifest and contents are pinned, but `latest` action, hosted runner, vulnerability DB and scanner tool dependencies can change. Each run records provenance; byte-identical image digests across changing builder versions are not promised.

Docker image ID is a content-addressed configuration digest. A registry manifest digest is a different quantity and is unavailable for this locally built, unpublished benchmark image. No benchmark image download size or compressed registry size is inferred from padding or `docker inspect`.

## Verified official action behavior

Inspected `latest` commit `6bed7e2ed5b6ec0ba0fe53cfe3d95792fe46d6eb`, [action.yaml](https://github.com/accuknox/container-scan-action/blob/6bed7e2ed5b6ec0ba0fe53cfe3d95792fe46d6eb/action.yaml):

* Despite its input description saying Dockerfile is optional for an existing image, the implementation unconditionally calls `docker build -t IMAGE:TAG -f DOCKERFILE .`.
* It downloads ASPM CLI v0.14.0, installs its container tool, runs the vulnerability scan with `--keep-results --container-mode`, and copies `results.json` to `results-vuln.json`.
* `upload_results` controls the GitHub artifact. Console uploading is performed by the scanner using its secret environment. Success must be verified from explicit upload evidence or tenant UI, not inferred from this input.
* `scripts/docker` transparently delegates Docker commands and measures the action's sole build with a monotonic timer. It validates metadata immediately after a successful build and before scanner execution. The workflow confirms the image ID again after scanning.

## Measurements and retrieval

Build time includes base-image download and image export. Action wall time includes build, scanner setup, database/network access, scan, console upload and the action's own artifact upload. These overlapping times must not be added together. Pure analysis, base pull, setup and console-upload timings are marked unavailable unless separately exposed by reliable logs. Artifact collection happens after summary creation; final job/workflow totals must be enriched using the completed Actions API metadata.

```bash
# Substitute a completed run ID. Work from the repository root.
gh run download RUN_ID --repo arpit175ak/metlifeimagescan --dir /tmp/metlife-artifacts-RUN_ID
gh api repos/arpit175ak/metlifeimagescan/actions/runs/RUN_ID/jobs > results/jobs.json
gh api repos/arpit175ak/metlifeimagescan/actions/runs/RUN_ID > results/run.json
# Copy the benchmark artifact's JSON measurements and report to results/ first.
python3 scripts/benchmark-summary.py
```

Raw logs can include tenant metadata; review before committing. Commit only non-sensitive, verified measurements and customer summaries. `results/verified-evidence.json`, when present, records explicit evidence and can enrich summary metrics; never populate it from assumptions.

Local build, when Docker is running:

```bash
docker build --platform linux/amd64 -t metlife-benchmark:latest -f Dockerfile .
bash scripts/verify-image.sh
python3 scripts/benchmark-summary.py
```

## Capacity limits

First confirm a successful baseline with actual findings and console-upload evidence. Only then implement controlled 5/10 concurrency after checking runner limits, using one immutable shared digest and comparable runners. Record actual overlapping execution intervals, queue delays, failures, batch start/end, sample count, mean and P95 (with method). Throughput is successful scans divided by elapsed batch hours. A single baseline is not a sustained capacity test.

Proposed on-premises sizing: 3 × (8 vCPU, 32 GB RAM, 500 GB storage) = 24 vCPU, 96 GB RAM, 1,500 GB storage. This is unvalidated. A local registry reduces external internet dependency, but local networking, registry performance, I/O, compute, scanner implementation and database availability remain relevant. Representative 1–3.5 GB images and sustained load, including 150 hourly base images, are required before claiming MetLife's hundreds-of-builds/hour target. SAST/SCA/Secrets are outside this container-only timing test.

## Observed registry failure and supported fallback

Initial run [39674424863](https://github.com/arpit175ak/metlifeimagescan/actions/runs/39674424863) built the fixture but failed before vulnerability analysis: the default `public.ecr.aws/k9v9d5v2/aquasec/trivy:0.65.0` returned `toomanyrequests: Data limit exceeded`. The verified [ASPM v0.14.0 implementation](https://github.com/accuknox/aspm-scanner-cli/blob/v0.14.0/aspm_cli/scan/container.py) supports the `SCAN_IMAGE` environment variable. The workflow uses `aquasec/trivy:0.65.0` from the scanner publisher on Docker Hub, keeping the official action unchanged and adding no action inputs or scanner flags. Scanner pulls remain part of the measured action.
