# MetLife AccuKnox container benchmark

Run: https://github.com/arpit175ak/metlifeimagescan/actions/runs/39675041921

| Metric | Actual result |
|---|---|
| CI/CD platform | GitHub Actions |
| Image name | metlife-benchmark:latest |
| Image digest | sha256:750e004ad2183cdd5d5d571626581d3a622ca2f6be1b01a61253082df97013f5 (local image configuration digest; not registry manifest digest) |
| Image size | 2,114,431,762 bytes (2.114 GB), Docker virtual/uncompressed size |
| Compressed registry image size | Unavailable: benchmark image is local and is not pushed to a registry |
| Image download size | Not separately measurable |
| Runner CPU/RAM | 4 logical CPUs / 15.61 GiB RAM |
| Scanner version | ASPM CLI v0.14.0 (download URL); container engine image aquasec/trivy:0.65.0 (configured version; binary --version not independently queried) |
| Build duration | 21.546 s (includes base-image acquisition and build export) |
| Image pull duration | Not separately measurable |
| Scanner setup/initialization duration | 2.869 s (CLI download and tool install only; scanner-container pull/database work follows) |
| Actual scanner analysis duration | Not separately measurable |
| AccuKnox action duration | 247.000 s (includes internal build, setup, database/network, scan and uploads) |
| Results upload duration | 4.175 s (client log interval; includes HTTP request/response) |
| Total CI/CD job duration | 253.000 s (includes runner job preparation and cleanup) |
| Total workflow duration | 257.000 s (creation to terminal update; includes queueing) |
| Vulnerability findings | 14353 package vulnerability records (not deduplicated CVEs) |
| Scan status | Completed with vulnerability findings; soft_fail accepted findings; successful HTTP console upload confirmed |
| Console upload status | Scanner confirmed successful HTTP upload; tenant UI ingestion/display not independently verified |
| Concurrent scans | Baseline 1; requested 5, observed peak action overlap 5; requested 10, observed peak action overlap 10 |
| Measured throughput | 61.22 successful scans/hour in 5-sample batch (5/5 verified); 113.56 successful scans/hour in 10-sample batch (10/10 verified); exploratory GitHub-hosted batch rates, not sustained on-premises capacity |
| Scanned image identity | Report Metadata.ImageID exactly matches the measured Docker image ID |
| Scanner-reported image size | 2,136,613,376 bytes (scanner metadata; size source differs from Docker inspect) |

The image contains pinned Python 3.9.18 / Debian 11 packages and 1,152 MiB of deterministic, highly compressible test padding. Its uncompressed size is deliberately above 1 GiB. This is a padded size fixture, not a representative 1 GB of application dependencies, compressed registry content, or transferred data. Findings must come from the actual report.

The official action builds once. A transparent Docker wrapper measures that build and verifies its image ID and size before the scanner starts. The image ID is checked again afterward. No benchmark image registry pull occurs: the scanner uses the local tag. Base-layer downloads are inside the build timer; scanner tooling/database downloads are inside action time. Internal analysis and console-upload phases are unavailable unless explicit scanner evidence exposes them. `upload_results` controls GitHub artifacts, not console upload.

GitHub-hosted results do not validate MetLife production throughput. Sanjay's proposal is 3 nodes, each 8 vCPU / 32 GB RAM / 500 GB storage: total 24 vCPU / 96 GB / 1,500 GB. This is proposed sizing only. A local registry and on-premises scanner can reduce external internet dependency; registry speed, storage I/O, CPU, RAM, scanner implementation, vulnerability database availability, cache state and workload composition still affect performance.

Varendra: use only the measured values above. Before committing to hundreds of builds per hour across 2,000–3,000 repositories, 3,000+ images and approximately 150 hourly base images, validate representative 1–3.5 GB images, cold/warm caches, database updates, security gating, and sustained controlled concurrency on the proposed on-premises environment. SAST, SCA and Secrets require their own benchmarks. No production capacity claim is made by this container test.

Controlled concurrency batches completed after the verified baseline; details follow. Queued jobs do not count as concurrent execution. Throughput = verified successful scans / elapsed batch hours; P95 requires a stated sample size and method.

## Completed controlled batches

| Requested / observed peak action overlap | Verified / failed or unverified | Batch seconds | Successful scans/hour | Mean action seconds | P95 action seconds |
|---|---|---|---|---|---|
| 5 / 5 | 5 / 0 | 294.000 | 61.22 | 214.600 | 232.0 |
| 10 / 10 | 10 / 0 | 317.000 | 113.56 | 196.000 | 238.0 |

| Batch | Mean archive download | Mean archive load | Mean scanner-container pull | Mean scanner invocation |
|---|---|---|---|---|
| 5 | 6.800 s | 36.852 s | 3.419 s | 198.370 s |
| 10 | 9.500 s | 33.623 s | 3.363 s | 179.725 s |

Scanner invocation includes container startup, database/network operations and default scanner analysis; it is not pure vulnerability analysis. Archive downloads and Actions step timestamps have one-second API resolution. The compressed Docker archive is distinct from a compressed registry manifest and network protocol overhead.

Measured shared Docker archive size: 381,424,882 bytes.

Batch time spans earliest runner-job start to latest runner-job completion, including fixture acquisition and artifacts. Dispatch-to-completion rates and per-sample UTC times/queue delays are recorded in each batch directory. P95 uses nearest rank; n=5/10 is exploratory. All concurrent samples use shared image configuration digest `sha256:c9ba3e0d62dc0596b4106e04564661f4127acfff8965eec2d9971604bbad585b`; the initial full-build baseline has its own digest above. A compressed archive is not a registry image. Cached FROM builds in shared-image samples differ from the full baseline build. Action overlap includes setup/scan/upload; pure analysis overlap is unavailable.

Initial failed attempt: [39674424863](https://github.com/arpit175ak/metlifeimagescan/actions/runs/39674424863), scanner-container pull, before vulnerability analysis: public.ecr.aws scanner image returned toomanyrequests: Data limit exceeded. Verified SCAN_IMAGE environment variable selects official aquasec/trivy:0.65.0 from Docker Hub; retry succeeded. This attempt is excluded from the subsequent successful batch rates, and remains recorded as a failed attempt.
