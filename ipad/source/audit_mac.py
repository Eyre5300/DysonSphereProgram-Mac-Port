"""Read-only audit of an owned Mac Unity input. No game content is exported."""
import argparse,hashlib,json,plistlib,subprocess
from pathlib import Path

def run(*a):return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT)
def audit(app):
    app=Path(app).resolve();info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
    files=[app/'Contents/MacOS'/info['CFBundleExecutable']]
    files+=sorted((app/'Contents/Frameworks').rglob('*.dylib'))
    binaries=[]
    for p in files:
        entry={'path':str(p.relative_to(app)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'architectures':run('lipo','-archs',str(p)).strip()}
        if 'arm64' in entry['architectures'].split():
            entry['dependencies']=run('otool','-arch','arm64','-L',str(p)).splitlines()[1:]
            entry['undefinedSymbols']=run('nm','-arch','arm64','-u',str(p)).splitlines()
        binaries.append(entry)
    managed=list((app/'Contents/Resources/Data/Managed').glob('*.dll'))
    aot=list((app/'Contents').rglob('*Assembly-CSharp*.dylib'))
    return {'schema':1,'app':str(app),'bundleVersion':info.get('CFBundleVersion'),'binaries':binaries,'managedDLLCount':len(managed),'managedAOTImageCount':len(aot),'backend':'Mono' if any('libmonobdwgc' in p.name for p in files) else 'unknown','fullGameOnIPadVerified':False}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    r=audit(a.app);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r['backend'],len(r['binaries']),'Mach-O files;',r['managedDLLCount'],'managed DLLs;',r['managedAOTImageCount'],'managed AOT images')
