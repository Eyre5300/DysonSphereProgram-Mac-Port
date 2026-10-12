#!/usr/bin/env python3
"""Stage the authored transport publication handshake into a private game copy."""
import argparse,shutil,hashlib,json
from pathlib import Path
from apply_managed_input_trace import insert_method_tail
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
vf=a.project/'Assets/Scripts/Assembly-CSharp/VFInput.cs';old=vf.read_text()
if 'using Input = DSPPadInput;' not in old or 'DSPPadInput.FixedInputSampled();' not in old:raise RuntimeError('Input foundation missing')
call='DSPPadInput.UpdateInputPublished()'
new=insert_method_tail(old,'OnUpdate',call)
if insert_method_tail(new,'OnUpdate',call)!=new:raise RuntimeError('Not idempotent')
print(json.dumps({'before':hashlib.sha256(old.encode()).hexdigest(),'after':hashlib.sha256(new.encode()).hexdigest(),'apply':a.apply}))
if a.apply:
 vf.write_text(new)
 for name in ('DSPPadKeyQueue.cs','DSPPadKeyboard.cs','DSPPadInput.cs'):shutil.copy2(Path(__file__).parent/name,a.project/'Assets'/name)
