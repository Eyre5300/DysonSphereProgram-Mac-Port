"""Use the existing Metal MSAA storage adapter on the original Milky Way UI target."""
from pathlib import Path
import argparse, hashlib, json
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
original=a.original.read_text();s=a.target.read_text()
anchor='\t\t\tmilkyWayRT.antiAliasing = 4;'
hook='\n#if DSP_EMU_IPAD\n\t\t\tPortMemorylessUI.Configure(milkyWayRT);\n#endif'
assert original.count(anchor)==1 and s.count(anchor)==1
before=s.replace(hook,'')
if hook not in s:s=s.replace(anchor,anchor+hook,1);a.target.write_text(s)
assert s.replace(hook,'')==before
assert original[original.index('private void CheckOrCreateRTex()'):original.index('private void ReleaseRTex()')]==before[before.index('private void CheckOrCreateRTex()'):before.index('private void ReleaseRTex()')]
a.report.write_text(json.dumps({'scope':'Only memoryless transient MSAA attachment; original dimensions/FP16/depth/samples/resolve unchanged. Device regression pending.','originalMethodBodyPreserved':True,'sourceSHA256':hashlib.sha256(original.encode()).hexdigest(),'targetSHA256':hashlib.sha256(s.encode()).hexdigest()},indent=2))
