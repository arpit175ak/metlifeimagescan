#!/usr/bin/env bash
set -euo pipefail
image="${1:-metlife-benchmark:latest}"
mkdir -p results
"${REAL_DOCKER:-docker}" image inspect "$image" > results/image-inspect.json
python3 - <<'PY'
import json
from pathlib import Path
x=json.loads(Path('results/image-inspect.json').read_text())[0]
m={'image':'metlife-benchmark:latest','image_id':x['Id'],'repo_digests':x.get('RepoDigests',[]),'uncompressed_bytes':x['Size'],'architecture':x['Architecture'],'os':x['Os'],'compressed_registry_bytes':None,'download_bytes':None}
Path('results/image-metadata.json').write_text(json.dumps(m,indent=2)+'\n')
assert m['uncompressed_bytes'] > 1073741824, 'Image must exceed both 1 GB and 1 GiB'
print(json.dumps(m,indent=2))
PY
