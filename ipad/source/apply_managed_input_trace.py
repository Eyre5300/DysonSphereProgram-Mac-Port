#!/usr/bin/env python3
"""Private diagnostic-only staging; preview by default, --apply explicit."""
import argparse,json,hashlib,shutil
from pathlib import Path
def insert_method_tail(source,name,call):
    signature='\tpublic static void '+name+'()'
    at=source.index(signature);start=source.index('{',at);depth=1;i=start+1
    while depth:
        if source[i]=='{':depth+=1
        elif source[i]=='}':depth-=1
        i+=1
    body=source[start+1:i-1]
    marker='\n#if DSP_EMU_IPAD\n\t\t'+call+';\n#endif\n'
    if call+';' in body:return source
    if not body.endswith('\n\t'):raise RuntimeError('Unexpected method tail: '+name)
    return source[:i-3]+marker+'\t'+source[i-1:]
def patch(source):
    return insert_method_tail(insert_method_tail(source,'OnUpdate','DSPPadManagedInputTrace.AfterUpdate()'),'OnFixedUpdate','DSPPadManagedInputTrace.AfterFixed()')
def strip(source):
    import re
    return re.sub(r'\n#if DSP_EMU_IPAD\n\t\tDSPPadManagedInputTrace.After(?:Update|Fixed)\(\);\n#endif\n', '\n',source)
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--rsp');p.add_argument('--apply',action='store_true');a=p.parse_args()
    root=Path(a.project);src=root/'Assets/Scripts/Assembly-CSharp/VFInput.cs';text=src.read_text();candidate=patch(text)
    if patch(candidate)!=candidate:raise RuntimeError('Not idempotent')
    if strip(candidate)!=strip(text):raise RuntimeError('Diagnostic calls changed original code')
    helper=Path(__file__).with_name('DSPPadManagedInputTrace.cs')
    print(json.dumps({'mode':'apply' if a.apply else 'preview','vfInputBefore':hashlib.sha256(text.encode()).hexdigest(),'vfInputAfter':hashlib.sha256(candidate.encode()).hexdigest(),'originalCodeUnchangedAfterStrip':True,'helper':str(helper),'runtimeInitializerRequired':False},indent=2))
    if a.apply:
        src.write_text(candidate);shutil.copy2(helper,root/'Assets'/helper.name)
        if a.rsp:
            rsp=Path(a.rsp);r=rsp.read_text();entry='"Assets/'+helper.name+'"'
            if entry not in r:rsp.write_text(r.rstrip()+'\n'+entry+'\n')
if __name__=='__main__':main()
