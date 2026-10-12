"""Generate a private SDK archive with authored BC symbol adapters. No SDK is distributed."""
import argparse,hashlib,json,subprocess,shutil,sys
from pathlib import Path
from private_paths import private_output

def digest(data):return hashlib.sha256(data).hexdigest()
def members(path):
    data=path.read_bytes()
    if data[:8]!=b'!<arch>\n':raise ValueError('Expected an ar archive')
    result={};offset=8
    while offset<len(data):
        header=data[offset:offset+60]
        if len(header)!=60 or header[58:]!=b'`\n':raise ValueError('Malformed archive')
        length=int(header[48:58]);name=header[:16].decode().strip();payload=data[offset+60:offset+60+length]
        if len(payload)!=length:raise ValueError('Truncated member')
        if name.startswith('#1/'):
            size=int(name[3:]);name=payload[:size].split(b'\0')[0].decode();payload=payload[size:]
        else:name=name.rstrip('/')
        if not name.startswith('__.SYMDEF'):
            if name in result:raise ValueError('Ambiguous member')
            result[name]=digest(payload)
        offset+=60+length+(length%2)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    original=a.archive.resolve();out=private_output(a.output,[original]);out.mkdir(parents=True,exist_ok=False)
    before=members(original);originalHash=digest(original.read_bytes());member='TextureFormatMetal_y0zou.o'
    obj=out/member
    with obj.open('wb') as f:subprocess.run(['xcrun','ar','-p',str(original),member],stdout=f,check=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('prepare_bc_object.py')),'--work',str(out)],check=True)
    receipt=json.loads((out/'candidate-object-receipt.json').read_text());candidate=out/'TextureFormatMetal_bc_candidate.o'
    if before[member]!=receipt['originalObjectSHA256']:raise ValueError('Archive member hash differs')
    dest=out/'libiPhone-bc-candidate.a';shutil.copy2(original,dest)
    subprocess.run(['xcrun','ar','-d',str(dest),member],check=True)
    subprocess.run(['xcrun','ar','-r',str(dest),str(candidate)],check=True)
    subprocess.run(['xcrun','ranlib',str(dest)],check=True)
    expected=dict(before);del expected[member];data=candidate.read_bytes();expected[candidate.name]=digest(data+b'\n'*((-len(data))%8))
    if members(dest)!=expected or digest(original.read_bytes())!=originalHash:raise ValueError('Unexpected archive changes')
    (out/'receipt.json').write_text(json.dumps({'originalArchiveSHA256':originalHash,'candidateArchiveSHA256':digest(dest.read_bytes()),'allOtherMembersExact':True,'changedMember':receipt,'deviceValidationRequired':True},indent=2))
    print('Private BC archive prepared; hardware/Unity sample validation still required.')
if __name__=='__main__':main()
