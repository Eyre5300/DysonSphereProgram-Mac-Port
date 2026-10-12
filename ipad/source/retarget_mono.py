"""Use emu's validated load-command primitives on a pinned owned Mono copy.

No instructions are patched; __text must remain identical. This only prepares
a loadability probe, not a functioning managed game or JIT workaround.
"""
import argparse,hashlib,json,plistlib,re,struct,subprocess,sys,shutil
from pathlib import Path

def prepare(source,output,upstream,expected,name="MacMono"):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*",name):raise ValueError("Invalid framework executable name")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('Mac input hash changed')
    sys.path.insert(0,str(upstream))
    from tools.macho import commands,code_hash,string_command,replace_commands,validate_dylib
    output.mkdir(parents=True,exist_ok=True);target=output/name
    archs=subprocess.check_output(['lipo','-archs',str(source)],text=True).split()
    if 'arm64' not in archs:raise ValueError('No ARM64 input slice')
    if len(archs)>1:subprocess.run(['lipo',str(source),'-thin','arm64','-output',str(target)],check=True)
    else:shutil.copy2(source,target)
    data=bytearray(target.read_bytes());validate_dylib(data);oldCode=code_hash(data)
    # Remove the signature on the private thin copy before changing load commands.
    # codesign also corrects __LINKEDIT; merely dropping LC_CODE_SIGNATURE leaves
    # an orphaned tail that Xcode's framework copy/strip validation rejects.
    subprocess.run(['codesign','--remove-signature',str(target)],check=True)
    data=bytearray(target.read_bytes());validate_dylib(data)
    if code_hash(data)!=oldCode:raise ValueError('Signature removal changed machine code')
    updated=[];routes=[];platform=False
    for kind,off,c in commands(data):
        if kind==0x1d:continue # Original code signature is replaced by Xcode.
        if kind==0x32:
            if struct.unpack_from('<I',c,8)[0]!=1:raise ValueError('Expected macOS input')
            struct.pack_into('<III',c,8,2,17<<16,27<<16);platform=True
        elif kind==0x24:
            c=bytearray(struct.pack('<IIIIII',0x32,24,2,17<<16,27<<16,0));platform=True
        elif kind==0xd:
            c=string_command(kind,c[8:24],f'@rpath/{name}.framework/{name}')
        elif kind in (0xc,0x80000018,0x8000001f):
            at=struct.unpack_from('<I',c,8)[0];old=c[at:].split(b'\0')[0].decode();new=re.sub(r'/Versions/[^/]+/','/',old)
            if old!=new:routes.append([old,new]);c=string_command(kind,c[8:24],new)
        updated.append(c)
    if not platform:raise ValueError('No supported macOS platform command')
    replace_commands(data,updated)
    if code_hash(data)!=oldCode:raise ValueError('Machine code changed')
    target.write_bytes(data);target.chmod(0o755)
    info={'CFBundleIdentifier':'local.dsp.emu.'+name.lower(),'CFBundleExecutable':name,'CFBundleName':name,'CFBundlePackageType':'FMWK','CFBundleVersion':'1','CFBundleShortVersionString':'0.1','MinimumOSVersion':'17.0','CFBundleSupportedPlatforms':['iPhoneOS']}
    (output/'Info.plist').write_bytes(plistlib.dumps(info))
    return {'inputSha256':expected,'arm64TextSha256':oldCode,'machineCodeUnchanged':True,'instructionsPatched':0,'routes':routes,'preparedSha256':hashlib.sha256(data).hexdigest(),'gameRuntimeStarted':False}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--upstream',required=True,type=Path);p.add_argument('--name',default='MacMono');p.add_argument('--sha256',required=True);p.add_argument('--report',required=True,type=Path);a=p.parse_args()
    r=prepare(a.source,a.output,a.upstream,a.sha256,a.name);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n');print(a.name+' ARM64 retargeted; __text identical; no game/JIT started.')
