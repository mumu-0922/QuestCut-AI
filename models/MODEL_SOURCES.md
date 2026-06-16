# Model Sources

QuestCut-AI bundles ONNX models locally so offline processing works without runtime downloads. Keep this file in sync whenever a model is replaced.

| Local path | Runtime key | Upstream file | Source URL | Size | MD5 | SHA256 |
| --- | --- | --- | --- | --- | --- | --- |
| `models/rembg/birefnet-general.onnx` | `birefnet` | `BiRefNet-general-epoch_244.onnx` | `https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-epoch_244.onnx` | 927.6 MiB / 972,666,916 bytes | `7a35a0141cbbc80de11d9c9a28f52697` | `58f621f00f5d756097615970a88a791584600dcf7c45b18a0a6267535a1ebd3c` |
| `models/rembg/birefnet-portrait.onnx` | `birefnet_portrait` | `BiRefNet-portrait-epoch_150.onnx` | `https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-portrait-epoch_150.onnx` | 927.6 MiB / 972,666,916 bytes | `c3a64a6abf20250d090cd055f12a3b67` | `1ba1c8ff5a7bbfadc8d8d13fb11d7be793f91f23d9d466549e37a854f6668f99` |
| `models/modnet/modnet.onnx` | `modnet` | `model.onnx` | `https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx` | 24.7 MiB / 25,888,640 bytes | `d0ded73e80bc0d38a64e2286486e4ea3` | `07c308cf0fc7e6e8b2065a12ed7fc07e1de8febb7dc7839d7b7f15dd66584df9` |

## Verification

Run this from the repository root after copying or updating model files:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib
for path in sorted(Path('models').rglob('*.onnx')):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    print(path, path.stat().st_size, h.hexdigest())
PY
```
