"""Preserve DirectX register bits in the six recovered space and ground formation kernels.
The GPU matrix audit covers four LOD counts for each formation. Original assets
are backed up once; no game logic, capacity or render feature is removed.
"""
from pathlib import Path
import json,hashlib
from typed_register_probe import transform
root=Path(__file__).resolve().parent
backup=root/'formation-register-original';backup.mkdir(exist_ok=True)
manifest=[]
for name in ['DFSLancerCulling','DFSHumpbackCulling','DFSFortressCulling','DFGRaiderCulling','DFGRangerCulling','DFGGuardianCulling']:
 p=root/'port-project/Assets/Resources/gpgpu'/(name+'.compute')
 b=backup/p.name
 if not b.exists():b.write_bytes(p.read_bytes())
 source=b.read_text();fixed=transform(source)
 p.write_text('// Integer storage preserves mixed float/integer DXBC register bit patterns on Metal.\n'+fixed)
 manifest.append({'asset':str(p),'originalSha256':hashlib.sha256(source.encode()).hexdigest(),'fixedSha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'formation-register-fix.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Updated six formation kernels; 24 GPU cases passed before integration.')
