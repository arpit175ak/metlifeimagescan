# MetLife AccuKnox container benchmark

| Metric | Actual result |
|---|---|
| CI/CD platform | GitHub Actions |
| Image name | Pending execution |
| Image digest | Pending execution |
| Image size | Pending build |
| Compressed registry image size | Unavailable: benchmark image is local and is not pushed to a registry |
| Image download size | Not separately measurable |
| Runner CPU/RAM | Pending execution |
| Scanner version | Pending runtime evidence |
| Build duration | Pending build |
| Image pull duration | Not separately measurable |
| Scanner setup/initialization duration | Not separately measurable |
| Actual scanner analysis duration | Not separately measurable |
| AccuKnox action duration | Pending completed job metadata |
| Results upload duration | Not separately measurable |
| Total CI/CD job duration | Pending completed job metadata |
| Total workflow duration | Pending completed run metadata |
| Vulnerability findings | Pending valid scan report |
| Scan status | Pending execution; scanner completion and tenant upload require separate verification |
| Console upload status | Pending explicit upload confirmation; a green action alone is insufficient |
| Concurrent scans | 1 baseline job configured; concurrency testing pending successful baseline |
| Measured throughput | Pending verified successful scans and completed batch timing |

The image contains pinned Python 3.9.18 / Debian 11 packages and 1,152 MiB of deterministic, highly compressible test padding. Its uncompressed size is deliberately above 1 GiB. This is a padded size fixture, not a representative 1 GB of application dependencies, compressed registry content, or transferred data. Findings must come from the actual report.

The official action builds once. A transparent Docker wrapper measures that build and verifies its image ID and size before the scanner starts. The image ID is checked again afterward. No benchmark image registry pull occurs: the scanner uses the local tag. Base-layer downloads are inside the build timer; scanner tooling/database downloads are inside action time. Internal analysis and console-upload phases are unavailable unless explicit scanner evidence exposes them. `upload_results` controls GitHub artifacts, not console upload.

GitHub-hosted results do not validate MetLife production throughput. Sanjay's proposal is 3 nodes, each 8 vCPU / 32 GB RAM / 500 GB storage: total 24 vCPU / 96 GB / 1,500 GB. This is proposed sizing only. A local registry and on-premises scanner can reduce external internet dependency; registry speed, storage I/O, CPU, RAM, scanner implementation, vulnerability database availability, cache state and workload composition still affect performance.

Varendra: use only the measured values above. Before committing to hundreds of builds per hour across 2,000–3,000 repositories, 3,000+ images and approximately 150 hourly base images, validate representative 1–3.5 GB images, cold/warm caches, database updates, security gating, and sustained controlled concurrency on the proposed on-premises environment. SAST, SCA and Secrets require their own benchmarks. No production capacity claim is made by this container test.

Concurrency levels 5 and 10 are pending a confirmed successful baseline, immutable shared image distribution and a review of GitHub runner limits. Queued jobs do not count as concurrent execution. Throughput = verified successful scans / elapsed batch hours; P95 requires a stated sample size and method.
