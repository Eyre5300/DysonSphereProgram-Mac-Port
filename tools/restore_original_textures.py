#!/usr/bin/env python3
"""Restore exact original BC texture bytes in a NEW Mac app copy, never recompress.

Input/output assets stay private. Unique name + dimensions + mip count mapping;
ambiguous, CPU-readable, non-BC and metadata-mismatched textures are skipped.
Existing object IDs, other objects, mip levels and renderer settings are retained.
Requires UnityPy 1.25.4. Experimental until game regression and memory tests pass.
"""
import argparse, collections, gc, hashlib, json, subprocess
from pathlib import Path
import UnityPy

BC_FORMATS = {10, 12, 24, 25} # DXT1, DXT5, BC6H, BC7; no encoding performed.
FIELDS = ('m_Width','m_Height','m_MipCount','m_ImageCount','m_TextureDimension',
          'm_ColorSpace','m_LightmapFormat','m_IsPreProcessed','m_MipsStripped')
def key(t):
    return tuple(t.get(k) for k in ('m_Name','m_Width','m_Height','m_MipCount'))
def digest(data):
    return hashlib.sha256(data).hexdigest()
def texture_rows(root):
    result=collections.defaultdict(list)
    for path in sorted(root.glob('*.assets')):
        env=UnityPy.load(str(path))
        for obj in env.objects:
            if obj.type.name!='Texture2D':continue
            t=obj.read_typetree()
            result[key(t)].append((path.name,obj.path_id,t))
        del env;gc.collect()
    return result

def restore(game, app, output, report_path, plan_only=False):
    game,app,output=game.resolve(),app.resolve(),output.resolve()
    public_root=Path(__file__).resolve().parents[1]
    if output==public_root or public_root in output.parents or report_path.resolve()==public_root or public_root in report_path.resolve().parents:
        raise ValueError('Generated app and private texture report must stay outside publishable tools')
    if output.exists():raise ValueError('Output exists; a new app path is required')
    if app in output.parents or output in app.parents or game in output.parents:
        raise ValueError('Output cannot overlap either input')
    if UnityPy.__version__!='1.25.4':raise ValueError('Validated serializer is UnityPy 1.25.4')
    source_root=game/'DSPGAME_Data';built_root=app/'Contents/Resources/Data'
    if not (source_root/'Managed/Assembly-CSharp.dll').is_file():raise ValueError('Windows input missing')
    if not (built_root/'resources.assets').is_file():raise ValueError('Mac app input missing')
    original=texture_rows(source_root);built=texture_rows(built_root)
    selected=collections.defaultdict(list);skipped=collections.Counter();saved=0
    for identity,targets in built.items():
        sources=original.get(identity,[])
        if len(sources)!=1 or len(targets)!=1:skipped['ambiguous_or_absent']+=len(targets);continue
        sf,si,s=sources[0];tf,ti,t=targets[0]
        if s.get('m_TextureFormat') not in BC_FORMATS or t.get('m_TextureFormat') not in BC_FORMATS:
            skipped['non_BC']+=1;continue
        if s.get('m_IsReadable') or t.get('m_IsReadable'):skipped['CPU_readable']+=1;continue
        if any(s.get(k)!=t.get(k) for k in FIELDS) or s.get('m_TextureSettings')!=t.get('m_TextureSettings'):
            skipped['metadata_mismatch']+=1;continue
        ss,ts=s.get('m_StreamData',{}),t.get('m_StreamData',{})
        if not ss.get('size') or not ts.get('size') or ss['size']>ts['size']:
            skipped['nonstream_or_expansion']+=1;continue
        if Path(ss['path']).name!=ss['path'] or Path(ts['path']).name!=ts['path']:
            raise ValueError('Unexpected resource path')
        saved+=ts['size']-ss['size']
        selected[tf].append((sf,si,s,ti,t))
    report={'status':'plan','originalAssemblySha256':digest((source_root/'Managed/Assembly-CSharp.dll').read_bytes()),
            'textures':sum(map(len,selected.values())),'texturePayloadReductionBytes':saved,
            'skipped':dict(skipped),'changes':[], 'notes':'Payload savings, not measured physical footprint. No texture size or mip reduction. Sparse unused tail bytes remain in the app stream files.'}
    if plan_only:
        report_path.write_text(json.dumps(report,indent=2));return report
    output.parent.mkdir(parents=True,exist_ok=True)
    # macOS clone-on-write copy; preserve the original, never edit in place.
    subprocess.run(['cp','-cR',str(app),str(output)],check=True)
    dest=output/'Contents/Resources/Data'
    for filename,items in selected.items():
        env=UnityPy.load(str(dest/filename));asset=env.file
        if not hasattr(asset,'objects'):raise ValueError('Expected one serialized asset file')
        before={o.path_id:digest(o.get_raw_data())for o in env.objects}
        changed=set();ranges=collections.defaultdict(list)
        for _,_,_,_,t in items:
            st=t['m_StreamData'];ranges[st['path']].append((st['offset'],st['offset']+st['size']))
        for stream,intervals in ranges.items():
            intervals.sort()
            if any(a[1]>b[0]for a,b in zip(intervals,intervals[1:])):raise ValueError('Overlapping texture streams')
        for sourcefile,sourceid,s,targetid,t in items:
            ss,ts=s['m_StreamData'],t['m_StreamData']
            with (source_root/ss['path']).open('rb')as f:f.seek(ss['offset']);raw=f.read(ss['size'])
            if len(raw)!=ss['size']:raise ValueError('Truncated original resource')
            with (dest/ts['path']).open('r+b')as f:f.seek(ts['offset']);f.write(raw)
            row={'name':t['m_Name'],'asset':filename,'pathID':targetid,'sourceAsset':sourcefile,'sourcePathID':sourceid,
                 'beforeFormat':t['m_TextureFormat'],'afterFormat':s['m_TextureFormat'],
                 'beforeBytes':ts['size'],'afterBytes':len(raw),'sha256':digest(raw)}
            t['m_TextureFormat']=s['m_TextureFormat'];t['m_CompleteImageSize']=s['m_CompleteImageSize'];t['m_StreamData']['size']=len(raw)
            asset.objects[targetid].save_typetree(t);changed.add(targetid);report['changes'].append(row)
        data=asset.save();del env;gc.collect();(dest/filename).write_bytes(data);del data
        check=UnityPy.load(str(dest/filename))
        if set(before)!=set(check.file.objects):raise ValueError('Serialized object set changed')
        for obj in check.objects:
            if obj.path_id not in changed and digest(obj.get_raw_data())!=before[obj.path_id]:
                raise ValueError('Unrelated object modified')
        for row in report['changes']:
            if row['asset']!=filename:continue
            t=check.file.objects[row['pathID']].read_typetree();st=t['m_StreamData']
            with (dest/st['path']).open('rb')as f:f.seek(st['offset']);raw=f.read(st['size'])
            if digest(raw)!=row['sha256'] or t['m_TextureFormat']!=row['afterFormat']:
                raise ValueError('Restored texture failed verification')
        del check;gc.collect()
        print(filename,len(items),'verified',flush=True)
    report['status']='verified_bytes';report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    subprocess.run(['codesign','--force','--deep','--sign','-',str(output)],check=True)
    subprocess.run(['codesign','--verify','--deep','--strict',str(output)],check=True)
    report['status']='verified_bytes_signed';report['localSignatureVerified']=True
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('game','app','output','report'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--plan',action='store_true');a=p.parse_args()
    r=restore(a.game,a.app,a.output,a.report,a.plan)
    print(json.dumps({k:v for k,v in r.items()if k!='changes'},indent=2))
if __name__=='__main__':main()
