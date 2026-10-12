"""Preserve the original DoF signed alpha on the iPad engine bridge."""
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--project',type=Path,required=True)
a=p.parse_args()
target=a.project/'Assets/Scripts/Assembly-CSharp/UnityEngine/PostProcessing/DepthOfFieldComponent.cs'
s=target.read_text()
original='RenderTextureFormat format = RenderTextureFormat.DefaultHDR;'
if s.count(original)!=1: raise RuntimeError('Unexpected original DoF allocation: stop for version review')
marker='if (DSPPadRenderFormats.AlphaHDRCandidate) format = RenderTextureFormat.ARGBHalf;'
if marker not in s:
 s=s.replace(original,original+'\n#if DSP_EMU_IPAD\n            // Signed CoC and bokeh coverage need alpha; do not use RGB-only HDR.\n            '+marker+'\n#endif',1)
 target.write_text(s)
print('Original DoF shader/parameters retained; iPad intermediate signed RGBA HDR enabled')
