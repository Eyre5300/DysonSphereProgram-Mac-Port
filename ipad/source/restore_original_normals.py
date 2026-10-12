"""Restore owned Windows normal payloads/channel layout in private staged iPad Data.
Recovered shaders decode X from alpha (DXT5nm). Unity's iOS import instead emits
RGB normals with constant alpha; changing only the shader backend is insufficient.
No recompression, texture resizing, shader/game logic or original input writes.
"""
import argparse,copy,gc,hashlib,json
from collections import defaultdict
from pathlib import Path
import UnityPy
from create_bc_manifest import scan,META
from private_paths import private_output

PIN='6c122e5443e6843979b4064050dfcb5e0d75577a0b64f6ae4111290238b33c12'
STREAM='port-original-normal-payloads.resS'
def sha(data):return hashlib.sha256(data).hexdigest()
def check(value,message):
    if not value:raise ValueError(message)
def payload(root,t):
    stream=t['m_StreamData']
    if not stream['size']:return bytes(t['image data'])
    name=stream['path'];check(Path(name).name==name and not(root/name).is_symlink(),'Unsafe texture stream')
    with(root/name).open('rb') as f:f.seek(stream['offset']);data=f.read(stream['size'])
    check(len(data)==stream['size'],'Truncated texture payload');return data

def restore(source,target):
    check(UnityPy.__version__=='1.25.4','Requires audited UnityPy 1.25.4')
    check(source!=target and source not in target.parents and target not in source.parents,'Input/output overlap')
    check(sha((source/'Managed/Assembly-CSharp.dll').read_bytes())==PIN,'Unsupported owned Windows version')
    original=scan(source);built=scan(target);selected=[]
    for key,items in built.items():
        for filename,pid,t in items:
            if t.get('m_LightmapFormat') not in (3,4):continue
            candidates=[x for x in original.get(key,[]) if x[2].get('m_LightmapFormat')==3]
            # Scene-only and Resources variants can share a texture name. Their
            # owning serialized asset is stable; never select by list ordering.
            if len(candidates)>1:candidates=[x for x in candidates if x[0]==filename]
            check(len(candidates)==1,'Missing/ambiguous original normal: '+str((filename,key)))
            sf,si,s=candidates[0]
            check(all(s.get(k)==t.get(k) for k in META if k!='m_LightmapFormat'),'Normal metadata mismatch: '+t['m_Name'])
            check(s['m_IsReadable']==t['m_IsReadable'] and s['m_TextureFormat'] in (4,12,25),'Unexpected normal encoding/readability')
            raw=payload(source,s)
            selected.append((filename,pid,t,s,raw,sf,si))
    check(len(selected)==372,'Expected all 372 normal textures')
    if all(t['m_LightmapFormat']==3 for _,_,t,_,_,_,_ in selected):
        for _,_,t,s,raw,_,_ in selected:check(t['m_TextureFormat']==s['m_TextureFormat'] and payload(target,t)==raw,'Previously restored normal differs')
        return {'status':'already-restored','count':372,'recompressed':False}
    check(all(t['m_LightmapFormat']==4 for _,_,t,_,_,_,_ in selected),'Mixed normal restoration state')
    out=target/STREAM;check(not out.exists(),'New normal stream already exists')
    grouped=defaultdict(list);records=[]
    with out.open('xb') as f:
        for filename,pid,t,s,raw,sf,si in selected:
            fixed=copy.deepcopy(t);fixed.pop("type",None)  # scan-only identity, not a serialized field
            for key in ('m_TextureFormat','m_LightmapFormat','m_CompleteImageSize'):fixed[key]=s[key]
            if t['m_StreamData']['size']:
                f.write(b'\0'*((-f.tell())%16));offset=f.tell();f.write(raw)
                fixed['m_StreamData']={'offset':offset,'size':len(raw),'path':STREAM}
            else:fixed['image data']=s['image data']
            grouped[filename].append((pid,fixed,sha(raw)))
            records.append({'asset':filename,'pathID':pid,'sourceAsset':sf,'sourcePathID':si,'name':s['m_Name'],'sourceFormat':s['m_TextureFormat'],'bytes':len(raw),'originalPayloadSHA256':sha(raw)})
    for filename,rows in grouped.items():
        env=UnityPy.load(str(target/filename));check(hasattr(env.file,'objects'),'Expected serialized file')
        before={o.path_id:sha(o.get_raw_data()) for o in env.objects};expected={pid:t for pid,t,_ in rows}
        for pid,t,_ in rows:env.file.objects[pid].save_typetree(t)
        (target/filename).write_bytes(env.file.save());del env;gc.collect()
        env=UnityPy.load(str(target/filename));check(set(env.file.objects)==set(before),'Object IDs changed')
        for o in env.objects:
            if o.path_id in expected:
                actual=o.read_typetree();want=expected[o.path_id]
                check(actual==want,'Restored normal metadata differs '+str((filename,o.path_id))+': '+repr({k:(str(want[k])[:120],str(actual.get(k))[:120]) for k in want if actual.get(k)!=want[k]}))
            else:check(sha(o.get_raw_data())==before[o.path_id],'Unrelated serialized object changed')
        for pid,_,digest in rows:check(sha(payload(target,env.file.objects[pid].read_typetree()))==digest,'Normal payload differs from original')
        del env;gc.collect()
    return {'status':'original-normal-payloads-restored','count':372,'recompressed':False,'originalChannelEncoding':'alpha/green','oldIOSChannelEncoding':'red/green with constant alpha','streamBytes':out.stat().st_size,'runtimeVerified':False,'textures':records}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source-data','target-data','report'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();source=a.source_data.resolve();target=private_output(a.target_data);report=private_output(a.report)
    result=restore(source,target);report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2));print(result['status'],result['count'])
