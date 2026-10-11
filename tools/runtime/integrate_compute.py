from pathlib import Path
import json,re,shutil
root=Path('work/dsp-runtime'); base=root/'recovered-project/ExportedProject'; game=root/'port-project'; probe=root/'preflight-project'
manifest=json.loads((root/'recovered-compute-manifest.json').read_text()); report=[]
for e in manifest:
    original=Path(e['original_asset']); rel=original.relative_to(base); target=(game/rel).with_suffix('.compute')
    guid=re.search(r'^guid: (\w+)',Path(str(original)+'.meta').read_text(),re.M).group(1)
    source=probe/e['path']; target.write_bytes(source.read_bytes())
    Path(str(target)+'.meta').write_text(f'fileFormatVersion: 2\nguid: {guid}\nComputeShaderImporter:\n  externalObjects: {{}}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
    for old in [game/rel,Path(str(game/rel)+'.meta')]:
        if old.exists(): old.unlink()
    report.append(dict(name=e['name'],path=str(target.relative_to(game)),guid=guid,kernels=e['kernels']))
(root/'integrated-compute-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print('Integrated',len(report),'compute shaders preserving original GUIDs')
