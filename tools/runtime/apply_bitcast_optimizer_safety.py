"""Preserve integer register bit patterns in DXBC-recovered Metal HLSL.
The preflight BitcastAudit reproduces incorrect constant folding with both
normal and disable_fastmath compilation. skip_optimizations metal is the
validated correctness workaround until integer register typing is recovered.
Only recovered shaders with integer min/max or loops are included here.
"""
from pathlib import Path
import re,json
r=Path('work/dsp-runtime');changed=[]
# These original effect programs previously reproduced transient corrupt tails
# under Metal optimization; preserve the independently validated workaround.
effects={
 'VF Shaders/Forward Spacecraft/DF Ant Flare Flame',
 'VF Shaders/Forward/Rocket Effect Instancing',
 'VF Shaders/Forward Spacecraft/Flare Flame Warship',
 'VF Shaders/Star Shaders/Star Flame',
 'VF Shaders/Forward Spacecraft/Flare Flame Relay',
 'VF Shaders/Forward Spacecraft/Formation Flare Flame',
 'VF Shaders/Forward/Gauss Turret Fire',
 'VF Shaders/Forward Spacecraft/Flare Flame',
 'VF Shaders/Forward Spacecraft/Flare Flame Tinder',
 'VF Shaders/Forward/Logistic Ship Effect Instancing'}
for p in (r/'port-project/Assets').rglob('*.shader'):
 s=p.read_text()
 if 'RecoveredVert' not in s or 'asfloat(' not in s:continue
 name=re.search(r'Shader\s+"([^"]+)"',s)
 if not ((name and name[1] in effects) or re.search(r'asfloat\((?:max|min)\(as(?:u)?int',s) or re.search(r'\b(?:for|while)\s*\(',s)):continue
 if '#pragma skip_optimizations metal' not in s:
  s=re.sub(r'(#pragma target [^\n]+)',r'\1\n#pragma skip_optimizations metal',s);p.write_text(s);changed.append(str(p))
(r/'bitcast-optimizer-safety.json').write_text(json.dumps(changed,indent=2));print(len(changed),'additional shaders with risky bitcast patterns protected')
