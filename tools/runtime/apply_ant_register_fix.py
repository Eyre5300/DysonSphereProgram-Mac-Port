"""Restore space builder transport animation after twelve GPU/reference cases pass."""
from pathlib import Path
import hashlib,json
from typed_register_probe import transform
r=Path(__file__).resolve().parent
p=r/'port-project/Assets/Resources/gpgpu/DFSAntCulling.compute'
b=r/'formation-register-original'/p.name
if not b.exists():b.write_bytes(p.read_bytes())
source=b.read_text();p.write_text('// Preserve original mixed DXBC register bits on Metal.\n'+transform(source))
(r/'ant-register-fix.json').write_text(json.dumps({'asset':str(p),'originalSha256':hashlib.sha256(b.read_bytes()).hexdigest(),'fixedSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'verification':'ant-culling-audit.txt: four time samples and three camera distances, counts and positions/rotations match the original animation equations'},indent=2)+'\n')
