"""Inventory owned original input consumers and their prepared counterparts.
Reports names, API references and hashes only; never exports recovered methods.
This is a structural review aid, not a gameplay-equivalence certificate.
"""
import argparse,hashlib,json,re
from pathlib import Path
ALIAS='#if DSP_EMU_IPAD\nusing Input = DSPPadInput;\n#endif\n'
READERS=re.compile(r'\b(?:VFInput|Input|Cursor|CombineKey)\.|\b(?:PointerEventData|EventTrigger|KeyCode)\b|\bOn(?:Pointer|Drag|Scroll|Submit|Cancel|Select|Deselect)\w*\s*\(')
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def inventory(original,prepared):
 rows=[]
 for source in sorted(original.rglob('*.cs')):
  text=source.read_text();refs=READERS.findall(text)
  if not refs:continue
  rel=source.relative_to(original);target=prepared/rel
  if not target.is_file():raise ValueError('Missing input consumer '+str(rel))
  adapted=target.read_text();bare=adapted.replace(ALIAS,'')
  rows.append({'file':str(rel),'references':len(refs),'identicalExceptPlatformAlias':text==bare,'originalSHA256':sha(text),'preparedSHA256':sha(adapted),'qualifiedInputReads':len(re.findall(r'UnityEngine.Input\.',adapted)),'directAPIs':sorted(set(re.findall(r'\bInput\.(\w+)',text)))})
 return {'scope':'all textual input/event consumers; differing methods require review; device behavior remains separate','consumers':len(rows),'identicalExceptPlatformAlias':sum(x['identicalExceptPlatformAlias'] for x in rows),'files':rows}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('original','prepared','report'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 from private_paths import private_output
 target=private_output(a.report,[a.original,a.prepared]);target.parent.mkdir(parents=True,exist_ok=True)
 result=inventory(a.original,a.prepared);target.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='files'}))
if __name__=='__main__':main()
