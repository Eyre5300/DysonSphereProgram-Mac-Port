"""Finalize an owned local test app without a second full resource allocation.

Run after Xcode has produced the executable/frameworks. The resource-copy build
phase must be disabled explicitly in prepare_engine_bridge. Never touches user
documents or input data. The final signature is checked before installation.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, shutil

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app', required=True, type=Path)
    p.add_argument('--data', required=True, type=Path)
    p.add_argument('--identity', required=True)
    p.add_argument('--entitlements', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    a = p.parse_args()
    app, data = a.app.resolve(), a.data.resolve()
    if app.suffix != '.app' or not (app / 'Info.plist').is_file():
        raise ValueError('Expected an existing generated app bundle')
    if not (data / 'globalgamemanagers').is_file():
        raise ValueError('Expected exported Unity resource data')
    target = app / 'Data'
    if target == data or data.is_relative_to(target):
        raise ValueError('Resources must be separate from the generated app')
    if target.exists():
        shutil.rmtree(target)  # Generated app resources only; never input data.
    subprocess.run(['cp', '-cR', str(data), str(target)], check=True)
    files = 0
    for f in data.rglob('*'):
        if f.is_file():
            if sha(f) != sha(target / f.relative_to(data)):
                raise ValueError('Resource clone mismatch: ' + str(f.relative_to(data)))
            files += 1
    subprocess.run(['codesign', '--force', '--sign', a.identity,
                    '--entitlements', str(a.entitlements),
                    '--generate-entitlement-der', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps({'resourceFilesExact': files,
                                    'signatureVerified': True,
                                    'resourceClone': 'APFS'}, indent=2))
    print('Resource clone and final signature verified:', files, 'files')

if __name__ == '__main__':
    main()
