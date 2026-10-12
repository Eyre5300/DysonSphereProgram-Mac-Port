"""Add only the UIKit transport of the original final cursor request."""
from pathlib import Path
import argparse,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--file',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
s=a.file.read_text();hook='\n#if DSP_EMU_IPAD\n\t\tDSPPadCursorBridge.SetRequested(lockCursor);\n#endif'
anchor='public static void SetLockCursorDirect(bool lockCursor)\n\t{'
if hook not in s:
 if s.count(anchor)!=1:raise RuntimeError('Expected original cursor method exactly once')
 t=s.replace(anchor,anchor+hook,1);a.file.write_text(t)
else:t=s
assert t.replace(hook,'')==s.replace(hook,'')
a.report.write_text(json.dumps({'onlyPlatformTransportAdded':True,'before':hashlib.sha256(s.encode()).hexdigest(),'after':hashlib.sha256(t.encode()).hexdigest(),'originalBodySHA256':hashlib.sha256(t.replace(hook,'').encode()).hexdigest()},indent=2))
