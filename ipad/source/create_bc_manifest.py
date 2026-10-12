"""Match original BC payloads to a local iOS export; never distribute generated metadata/assets."""
import argparse,collections,gc,hashlib,json
from pathlib import Path
import UnityPy
from private_paths import private_output
META=['type','m_Name','m_Width','m_Height','m_Depth','m_MipCount','m_TextureDimension','m_LightmapFormat','m_ColorSpace','m_TextureSettings','m_IsPreProcessed','m_MipsStripped','m_ImageCount']
def digest(path,offset=0,size=None):
    h=hashlib.sha256()
    with path.open('rb') as f:
        f.seek(offset)
        while size is None or size>0:
            block=f.read(1048576 if size is None else min(size,1048576))
            if not block:break
            h.update(block)
            if size is not None:size-=len(block)
    if size:raise ValueError('Truncated payload')
    return h.hexdigest()
def scan(root):
    result=collections.defaultdict(list)
    for file in sorted(root.glob('*.assets')):
        env=UnityPy.load(str(file))
        for obj in env.objects:
            if obj.type.name not in ('Texture2D','Cubemap'):continue
            t=obj.read_typetree();t['type']=obj.type.name;s=t.get('m_StreamData',{})
            # Inline/readable textures must still count for ambiguous-name exclusion.
            if s.get('size') and s.get('path') and (Path(s['path']).name!=s['path'] or (root/s['path']).is_symlink()):raise ValueError('Unsafe stream path')
            key=tuple(t.get(k) for k in ['type','m_Name','m_Width','m_Height','m_MipCount'])
            result[key].append((file.name,obj.path_id,t))
        del env;gc.collect()
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['source-data','target-data','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();source=a.source_data.resolve();target=a.target_data.resolve();out=private_output(a.output,[source,target]);sa=scan(source);ta=scan(target);rows=[]
    for key in sorted(ta,key=str):
        if len(ta[key])!=1 or len(sa.get(key,[]))!=1:continue
        sf,si,s=sa[key][0];tf,ti,t=ta[key][0]
        if s['m_TextureFormat'] not in (10,12,24,25) or s.get('m_IsReadable') or t.get('m_IsReadable'):continue
        if s.get('m_LightmapFormat') in (3,4) or t.get('m_LightmapFormat') in (3,4):continue
        if any(s.get(k)!=t.get(k) for k in META):continue
        ss,ts=s.get('m_StreamData',{}),t.get('m_StreamData',{})
        if not all(x.get('size') and x.get('path') for x in [ss,ts]):continue
        if ss['size']>ts['size']:continue
        rows.append({'name':s['m_Name'],'sourceAsset':sf,'sourcePathID':si,'targetAsset':tf,'targetPathID':ti,'sourceFormat':s['m_TextureFormat'],'targetFormat':t['m_TextureFormat'],'sourceStream':ss,'targetStream':ts,'sourcePayloadSHA256':digest(source/ss['path'],ss['offset'],ss['size']),'targetPayloadSHA256':digest(target/ts['path'],ts['offset'],ts['size']),'metadata':{k:s.get(k) for k in META},'sourceBytes':ss['size'],'targetBytes':ts['size'],'payloadSavings':ts['size']-ss['size']})
    savings=sum(x['payloadSavings'] for x in rows)
    if len(rows)!=2234 or savings!=619998464:
        out.parent.mkdir(parents=True,exist_ok=True);out.with_suffix('.rejected.json').write_text(json.dumps(rows,indent=2))
        raise ValueError(f'Export differs: {len(rows)} objects / {savings} bytes, expected 2234 / 619998464; inspect, do not bypass')
    report={'windowsAssemblySHA256':digest(source/'Managed/Assembly-CSharp.dll'),'count':len(rows),'savings':savings,'textures':rows}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Manifest SHA256:',digest(out))
if __name__=='__main__':main()
