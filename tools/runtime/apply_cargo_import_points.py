"""Preserve imported path poses; defer only unused zero tail on Apple Metal Mac."""
import argparse,hashlib
from pathlib import Path
SUPPORTED_SOURCE_SHA='2adddcd9d53980184d95f4f291c943356c1afa79edea7d2617bf4b580b1decc5'
IMPORT_OLD='\t\tSetCapacity(r.ReadInt32());\n\t\tbufferLength = r.ReadInt32();'
IMPORT_NEW='\t\tif (PortCargoImportedPoints.Supported && PortCargoImportedPoints.Enabled)\n\t\t\tPortCargoImportedPoints.ReadCapacity(r, ref capacity, ref bufferLength, ref buffer, ref pointPos, ref pointRot);\n\t\telse\n\t\t{\n\t\t\tSetCapacity(r.ReadInt32());\n\t\t\tbufferLength = r.ReadInt32();\n\t\t}'
METHODS=('SetCapacity(int newCap)','AddBuffer(int length, int speed, Vector3[] posAdd, Quaternion[] rotAdd, Vector3 posOffset)','PathConcat(CargoPath other)','PathCopy(CargoPath srcPath, int srcBegin)','PathOpen(int openIdx)')
RESTORE='\t\tPortCargoImportedPoints.Restore(ref pointPos, ref pointRot, capacity);\n'
def transformed(source):
 patched=IMPORT_NEW in source or RESTORE in source
 original=source
 if patched:
  if source.count(IMPORT_NEW)!=1 or source.count(RESTORE)!=len(METHODS):raise ValueError('Partial cargo geometry patch')
  original=source.replace(IMPORT_NEW,IMPORT_OLD,1)
  for method in METHODS:
   anchor='\tpublic void '+method+'\n\t{\n'
   if original.count(anchor+RESTORE)!=1:raise ValueError('Unsupported cargo mutation guard: '+method)
   original=original.replace(anchor+RESTORE,anchor,1)
 if hashlib.sha256(original.encode()).hexdigest()!=SUPPORTED_SOURCE_SHA:raise ValueError('Unsupported Windows CargoPath source; keep original version')
 if original.count(IMPORT_OLD)!=1:raise ValueError('Unsupported cargo import header')
 result=original.replace(IMPORT_OLD,IMPORT_NEW,1)
 for method in METHODS:
  anchor='\tpublic void '+method+'\n\t{\n'
  if result.count(anchor)!=1:raise ValueError('Unsupported cargo mutation anchor: '+method)
  result=result.replace(anchor,anchor+RESTORE,1)
 if patched and result!=source:raise ValueError('Cargo patch differs from validated layout')
 return result

def apply(project):
 p=Path(project)/'Assets/Scripts/Assembly-CSharp/CargoPath.cs';source=p.read_text();result=transformed(source)
 if result!=source:p.write_text(result)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
