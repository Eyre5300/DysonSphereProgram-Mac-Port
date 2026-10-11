"""Batch intermediate instance uploads only during the original initial factory load."""
import argparse,re
from pathlib import Path
COUNTS={'ObjectRenderer':(12,1),'InserterRenderer':(9,2),'DynamicRenderer':(6,2),'LabRenderer':(9,2),'VegeRenderer':(6,2)}
GUARD='if (!PortInitialInstanceUploads.Defer(this)) '
def apply(project):
 base=Path(project)/'Assets/Scripts/Assembly-CSharp';pending=[]
 for name,(expected,synced) in COUNTS.items():
  path=base/(name+'.cs');source=path.read_text()
  syncs=list(re.finditer(r'public (?:virtual|override) void SyncInstBuffer\(\)\s*\{[^}]*\}',source))
  calls=list(re.finditer(r'\b\w+Buffer\.SetData\([^;]+\);',source))
  if len(syncs)!=1 or len(calls)!=expected:raise ValueError('Unsupported instance upload layout: '+name)
  sync=syncs[0];active=[m for m in calls if not(sync.start()<=m.start()<sync.end())]
  if len(calls)-len(active)!=synced or GUARD in sync.group():raise ValueError('Original complete sync changed: '+name)
  guarded=[source[max(0,m.start()-len(GUARD)):m.start()]==GUARD for m in active]
  if any(guarded):
   if not all(guarded) or source.count(GUARD)!=len(active):raise ValueError('Partial instance upload patch: '+name)
   pending.append((path,source,source));continue
  if GUARD in source:raise ValueError('Unexpected instance upload guard: '+name)
  text=source
  for m in reversed(active):text=text[:m.start()]+GUARD+m.group()+text[m.end():]
  pending.append((path,source,text))
 # Validate all five original complete-sync methods before any write.
 for path,source,text in pending:
  if text!=source:path.write_text(text)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
