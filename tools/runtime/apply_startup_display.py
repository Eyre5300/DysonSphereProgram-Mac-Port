#!/usr/bin/env python3
"""Configure native fullscreen immediately before the original startup option Apply."""
import argparse
from pathlib import Path

ANCHOR='\tprivate void Start()\n\t{\n\t\tNewVersionOverrideOptions();\n\t\tglobalOption.Apply();'
HOOK='\t\tPortDisplayPresets.ConfigureStartup(ref globalOption);\n'
PATCHED=ANCHOR.replace('\t\tglobalOption.Apply();',HOOK+'\t\tglobalOption.Apply();')

def apply(project):
 path=Path(project)/'Assets/Scripts/Assembly-CSharp/DSPGame.cs';s=path.read_text()
 if HOOK in s:
  if s.count(HOOK)!=1 or s.count(PATCHED)!=1:raise ValueError('Partial or moved startup display hook')
  return
 if s.count(ANCHOR)!=1:raise ValueError('Unsupported original DSPGame startup; options must load before native display override')
 path.write_text(s.replace(ANCHOR,PATCHED,1))
 print('Native fullscreen at original option startup applied; later user Apply unchanged')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
