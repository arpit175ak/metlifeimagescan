# Technical summary for Varendra Maurya

Varendra, we completed a real AccuKnox container scan through GitHub Actions on a **2.114 GB image**, measured as **2,114,431,762 Docker virtual/uncompressed bytes**. It uses pinned Python/Debian packages and deterministic, highly compressible padding; this is not a 1 GB compressed download or a representative production application dependency set.

The full-build baseline took **247 seconds for the official AccuKnox action**, **253 seconds for the job**, and **257 seconds from workflow creation to completion**. Build time was **21.546 seconds**, CLI download/tool installation **2.869 seconds**, and the client-side console-upload interval **4.175 seconds**. These phases overlap the action total and must not be added to it. Base-image downloads are inside build time. Pure vulnerability analysis and vulnerability-database download times were **not separately measurable**.

The report contained **14,353 package vulnerability records** (9,637 unique vulnerability identifiers; these are not all distinct CVEs), including **248 CRITICAL** and **2,716 HIGH** records. The report's image ID exactly matched the measured image. The scanner explicitly confirmed successful HTTP upload to the configured AccuKnox endpoint. Tenant UI ingestion/display has **not been independently checked**.

After the successful baseline, we completed controlled batches on one shared image ID:

| Requested / observed peak overlapping actions | Verified scans / failed or unverified | Batch elapsed | Successful scans/hour | Mean action latency | P95 action latency |
|---|---|---|---|---|---|
| 5 / 5 | 5 / 0 | 294 s | 61.22 | 214.6 s | 232 s |
| 10 / 10 | 10 / 0 | 317 s | 113.56 | 196.0 s | 238 s |

Batch elapsed time includes image acquisition, scanning, uploads and job overhead, from earliest job start to latest completion. Including dispatch/queueing, rates were **60.38** and **111.74 scans/hour**. P95 uses nearest rank with only 5/10 samples, so it is exploratory. Shared-image samples use a cached FROM build; the baseline includes a full build. These short batches do not establish sustained throughput.

The shared Docker archive was **381,424,882 bytes**, distinct from registry image size and wire-protocol overhead. Mean archive download/load times were **6.8 / 36.852 seconds** at five jobs and **9.5 / 33.623 seconds** at ten. Mean scanner-container pulls were **3.419** and **3.363 seconds**, respectively. Scanner-invocation times still include database/network operations and other scanner work, so they are not pure vulnerability analysis.

All measured runners had **4 logical CPUs and approximately 15.6 GiB RAM**. GitHub-hosted results do not demonstrate MetLife's strictly on-premises production capacity. Sanjay's proposed sizing remains **3 nodes × 8 vCPU, 32 GB RAM, 500 GB storage**: total **24 vCPU, 96 GB RAM, 1,500 GB storage**, not yet validated.

An on-premises registry and scanner can reduce external internet dependency. Performance still depends on registry speed, local networking, storage I/O, CPU, RAM, scanner implementation, vulnerability database availability and cache state. Before claiming hundreds of builds per hour for 2,000–3,000 repositories / 3,000+ images plus approximately 150 hourly base images, validate representative 1–3.5 GB application images, cold/warm databases and caches, security gating and sustained concurrent load on the proposed infrastructure. SAST, SCA and Secrets need separate product/use-case validation.

The initial default scanner-image pull failed due to the public ECR data limit. The unmodified official action succeeded with its scanner's verified `SCAN_IMAGE` environment override pointing to the same configured Trivy version on the publisher's Docker Hub repository. That failed attempt remains recorded and is excluded from subsequent batch rates.

Source baseline: https://github.com/arpit175ak/metlifeimagescan/actions/runs/39675041921
Full metrics, UTC timestamps, sample run URLs and reproducibility notes: [benchmark-summary.md](benchmark-summary.md) and the batch evidence directories.
