#!/usr/bin/env python3
"""Route original mouse readers to one iPad-only platform transport.
No recovered source, assets or user data are included in this installer.
"""
import argparse, hashlib, json, pathlib, re
ALIAS='#if DSP_EMU_IPAD\nusing Input = DSPPadInput;\n#endif\n'
PATTERN=re.compile(r'\bInput\.(?:mousePosition|GetMouseButton(?:Down|Up)?)\b|\bInput\.Get(?:Key(?:Down|Up)?|Axis)\s*\([^\n;]*(?:KeyCode\.Mouse[0-6]|"Mouse (?:X|Y|Wheel)")')

def apply(project):
    base=project/'Assets'/'Scripts'/'Assembly-CSharp'
    if not base.is_dir():raise ValueError('Expected private, reconstructed Assembly-CSharp folder')
    report=[]
    for path in sorted(base.rglob('*.cs')):
        raw=path.read_bytes();bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        text=raw[len(bom):].decode('utf-8')
        if not PATTERN.search(text):continue
        if 'using Input = DSPPadInput;' in text:
            # Existing platform alias is intentionally retained byte for byte.
            report.append({'file':str(path.relative_to(project)),'changed':False});continue
        if re.search(r'\busing\s+Input\s*=',text):raise ValueError('Unexpected Input alias: '+str(path))
        new=bom+(ALIAS+text).encode('utf-8')
        if new[len(bom):].decode('utf-8').removeprefix(ALIAS)!=text:raise AssertionError('Original source preservation failed')
        path.write_bytes(new)
        report.append({'file':str(path.relative_to(project)),'changed':True,'originalSHA256':hashlib.sha256(raw).hexdigest(),'newSHA256':hashlib.sha256(new).hexdigest(),'gameMethodBodiesUnchanged':True})
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True,type=pathlib.Path);p.add_argument('--receipt',type=pathlib.Path)
    a=p.parse_args();r=apply(a.project.resolve())
    if a.receipt:a.receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({'mouseReaders':len(r),'newAliases':sum(x['changed'] for x in r),'allOriginalMethodsUnchanged':True}))
