#!/usr/bin/env python3
"""Keep native symmetric perspective projection on the tested Apple Metal Mac path."""
import argparse,hashlib
from pathlib import Path
SUPPORTED_SOURCE_SHA='9775f96733b42fb3e6f860ab565d8ca7e3742af6306263d575b94fe6537cfe43'
ANCHOR='\t\tMatrix4x4 projectionMatrix = Matrix4x4.Perspective(main.fieldOfView, main.aspect, main.nearClipPlane, main.farClipPlane);'
HOOK='\t\tif (PortCameraProjection.TryReset(main, m)) return;\n'
def apply(project):
 path=Path(project)/'Assets/Scripts/Assembly-CSharp/GameCamera.cs';s=path.read_text()
 if HOOK in s:
  if s.count(HOOK)!=1 or HOOK+ANCHOR not in s:raise ValueError('Partial or moved camera projection guard')
  original=s.replace(HOOK,'',1)
 else:original=s
 if hashlib.sha256(original.encode()).hexdigest()!=SUPPORTED_SOURCE_SHA:raise ValueError('Unsupported Windows GameCamera source; retain original camera logic')
 if original.count(ANCHOR)!=1:raise ValueError('Camera projection anchor count mismatch')
 if HOOK not in s:path.write_text(s.replace(ANCHOR,HOOK+ANCHOR,1))
 print('Mac symmetric camera projection adapter applied; original off-axis branch unchanged')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
