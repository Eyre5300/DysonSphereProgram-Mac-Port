"""Apply the iPad-only TextAsset borrowed read stream to the known private source."""
import argparse
import hashlib
import json
from pathlib import Path

ORIGINAL_SHA256 = '054e6838b8285ceabe0ce6118e4f05b092f095d2606c2d2e6ae1194e70f9541e'
OLD = '\t\tusing MemoryStream input = new MemoryStream(Configs.builtin.bucketMap.bytes);'
NEW = '#if DSP_EMU_IPAD\n\t\tusing Stream input = DSPPadTextAssetStream.OpenRead(Configs.builtin.bucketMap);\n#else\n' + OLD + '\n#endif'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    raw = a.original.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise SystemExit('Unrecognized original HashSystem: inspect the same-version Windows source first')
    original = raw.decode('utf-8')
    if original.count(OLD) != 1:
        raise SystemExit('Original stream construction is not unique')
    expected = original.replace(OLD, NEW)
    current = a.target.read_text()
    if current not in (original, expected):
        raise SystemExit('Target contains other changes; refusing to overwrite')
    changed = current != expected
    if changed:
        a.target.write_text(expected)
    assert a.target.read_text().replace(NEW, OLD) == original
    assert a.original.read_bytes() == raw
    report = {'changed': changed, 'originalSHA256': ORIGINAL_SHA256,
              'targetSHA256': hashlib.sha256(a.target.read_bytes()).hexdigest(),
              'originalDecoderExact': True, 'originalAssetUnchanged': True,
              'scope': 'Only the iPad Stream constructor is adapted; device lifetime and memory verification are separate.'}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
