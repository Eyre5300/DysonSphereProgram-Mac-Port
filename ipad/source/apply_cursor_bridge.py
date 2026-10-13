"""Transport original cursor requests and read back the platform-granted lock."""
from pathlib import Path
import argparse,json,hashlib
HOOK='\n#if DSP_EMU_IPAD\n\t\tDSPPadCursorBridge.SetRequested(lockCursor);\n#endif'
GETTER='public static bool locked => Cursor.lockState == CursorLockMode.Locked;'
BRIDGED='''#if DSP_EMU_IPAD
public static bool locked => DSPPadCursorBridge.Locked;
#else
\t'''+GETTER+'''
#endif'''
def patch(s):
 t=s
 anchor='public static void SetLockCursorDirect(bool lockCursor)\n\t{'
 if HOOK not in t:
  if t.count(anchor)!=1:raise RuntimeError('Expected original cursor method exactly once')
  t=t.replace(anchor,anchor+HOOK,1)
 if BRIDGED not in t:
  if t.count(GETTER)!=1:raise RuntimeError('Expected original cursor getter exactly once')
  t=t.replace(GETTER,BRIDGED,1)
 def strip(v):return v.replace(HOOK,'').replace(BRIDGED,GETTER)
 if strip(t)!=strip(s):raise RuntimeError('Original cursor policy changed')
 return t
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--file',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 s=a.file.read_text();t=patch(s);a.file.write_text(t)
 a.report.write_text(json.dumps({'platformRequestAndGrantedReadback':True,'originalPolicyUnchanged':True,'before':hashlib.sha256(s.encode()).hexdigest(),'after':hashlib.sha256(t.encode()).hexdigest()},indent=2))
