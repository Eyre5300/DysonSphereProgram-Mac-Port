#!/usr/bin/env python3
"""Strict private original-BC plan/apply for the audited 2234 iPad objects.
Default is read-only validation/plan. Apply requires a fresh private Data copy and
successful actual-Unity native-format sample report. Never edits input Data.
"""
import argparse,collections,copy,gc,hashlib,json,subprocess,sys
from pathlib import Path
import UnityPy
META=('m_Name','m_Width','m_Height','m_Depth','m_MipCount','m_TextureDimension','m_LightmapFormat','m_ColorSpace','m_TextureSettings','m_IsPreProcessed','m_MipsStripped','m_ImageCount')
BC={10,12,24,25}
def check(ok,message):
 if not ok:raise ValueError(message)
def digest(path,offset=0,size=None):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  f.seek(offset)
  while size is None or size>0:
   b=f.read(1048576 if size is None else min(size,1048576))
   if not b:break
   h.update(b)
   if size is not None:size-=len(b)
 check(size in (None,0),'Truncated file '+str(path));return h.hexdigest()
def name(value):
 check(value and Path(value).name==value and value not in ('.','..'),'Non-local asset/stream path');return value
def inside(path,root):return path==root or root in path.parents
def private_output(path,source,target):
 check(not inside(path,source) and not inside(path,target),'Output overlaps input')
 check('port-tools' not in path.parts,'Private output may not enter public port-tools')
 check(inside(path,Path('/private/tmp')) or 'local-private' in path.parts,'Output must be private tmp or local-private')
def load_asset(root,filename):
 check(not (root/name(filename)).is_symlink(),'Selected asset cannot be a symlink');env=UnityPy.load(str(root/name(filename)));check(hasattr(env.file,'objects'),'Expected serialized file');return env

def inspect(root,rows,prefix):
 """Verify every pinned object meta+payload, collect target stream alias coverage."""
 grouped=collections.defaultdict(list)
 for row in rows:grouped[row[prefix+'Asset']].append(row)
 selected={};asset_hashes={};stream_hashes={};all_ranges=collections.defaultdict(list)
 for filename,items in grouped.items():
  env=load_asset(root,filename);asset_hashes[filename]=digest(root/filename)
  for row in items:
   pid=row[prefix+'PathID'];check(pid in env.file.objects,'Missing object '+str(pid));obj=env.file.objects[pid];t=obj.read_typetree()
   check(obj.type.name==row['metadata']['type'] and obj.type.name in ('Texture2D','Cubemap'),'Texture type mismatch')
   check(all(t.get(k)==row['metadata'].get(k) for k in META),'Metadata mismatch '+row['name'])
   check(t.get('m_IsReadable') is False,'CPU-readable object '+row['name'])
   check(t.get('m_LightmapFormat') not in (3,4),'Platform-specific normal decode excluded')
   check(t['m_TextureFormat']==row[prefix+'Format'],'Format mismatch '+row['name'])
   stream=t['m_StreamData'];check(stream==row[prefix+'Stream'],'Stream metadata mismatch '+row['name']);name(stream['path']);check(not(root/stream['path']).is_symlink(),'Selected stream cannot be a symlink')
   check(stream['size']==row[prefix+'Bytes'],'Stream size mismatch')
   check(digest(root/stream['path'],stream['offset'],stream['size'])==row[prefix+'PayloadSHA256'],'Payload SHA mismatch '+row['name'])
   selected[(filename,pid)]=t
  if prefix=='target':
   # Include unselected texture/mesh streams to prohibit overwriting any aliased span.
   for obj in env.objects:
    if obj.type.name not in ('Texture2D','Cubemap','Texture3D','Texture2DArray','CubemapArray','Mesh'):continue
    t=obj.read_typetree();s=t.get('m_StreamData')
    if s and s.get('size') and s.get('path'):
     name(s['path']);all_ranges[s['path']].append((s['offset'],s['offset']+s['size'],filename,obj.path_id))
  del env;gc.collect();print(prefix,filename,len(items),'objects validated',flush=True)
 for row in rows:
  s=row[prefix+'Stream'];p=s['path']
  if p not in stream_hashes:stream_hashes[p]=digest(root/p)
 if prefix=='target':
  for row in rows:
   s=row['targetStream'];owner=(row['targetAsset'],row['targetPathID']);a,b=s['offset'],s['offset']+s['size']
   conflicts=[r for r in all_ranges[s['path']] if (r[2],r[3])!=owner and a<r[1] and r[0]<b]
   check(not conflicts,'Overlapping/aliased texture or mesh payload '+row['name'])
 return selected,asset_hashes,stream_hashes

def references(asset):
 return {'externals':[(x.path,x.temp_empty,x.guid.hex() if x.guid else None,x.type)for x in asset.externals],
         'scriptTypes':[(x.local_serialized_file_index,x.local_identifier_in_file)for x in asset.script_types]}
def write_report(path,report):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
def verify_sample(path):
 s=json.loads(path.read_text());check(s.get('status')=='sampled-subset-pass' and s.get('sampledSubsetPassed') is True and s.get('nativeFormatVerificationAvailable') is True,'Actual Unity BC sample report must pass with native format verification')
 check(not s.get('errors') and len(s.get('results',[]))==233,'Incomplete or failed Unity sample report')
 check(len({r['fixture']for r in s['results']})==12,'Expected all12 sample fixtures')
 for r in s['results']:check(r.get('passed') and r.get('expectedNativeFormat') and r.get('actualNativeFormat')==r['expectedNativeFormat'] and r.get('sourceNativeFormat')==r['expectedNativeFormat'],'Native BC sample result failed')
 return digest(path)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for arg in ('manifest','source-data','target-data','report'):p.add_argument('--'+arg,type=Path,required=True)
 p.add_argument('--manifest-sha256',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--output-data',type=Path);p.add_argument('--validated-sample-report',type=Path);a=p.parse_args()
 source,target=a.source_data.resolve(),a.target_data.resolve();report_path=a.report.resolve();private_output(report_path,source,target)
 report={'status':'validating','inputDataUnchanged':False,'operation':'apply' if a.apply else 'plan','manifestSHA256':digest(a.manifest),'changes':[]}
 try:
  check(UnityPy.__version__=='1.25.4','Requires audited UnityPy1.25.4');check(report['manifestSHA256']==a.manifest_sha256,'Local manifest digest mismatch')
  m=json.loads(a.manifest.read_text());rows=m['textures']
  check(len(rows)==m['count']==2234 and sum(r['payloadSavings']for r in rows)==m['savings']==619998464,'Manifest totals mismatch')
  check(digest(source/'Managed/Assembly-CSharp.dll')==m['windowsAssemblySHA256'],'Original Windows assembly mismatch')
  check(len({(r['sourceAsset'],r['sourcePathID'])for r in rows})==2234 and len({(r['targetAsset'],r['targetPathID'])for r in rows})==2234,'Duplicate object selection')
  for r in rows:
   check(r['sourceFormat']in BC and r['sourceBytes']<=r['targetBytes'] and r['sourceBytes']>0,'Invalid BC or payload expansion')
   check(r['targetBytes']-r['sourceBytes']==r['payloadSavings'],'Savings mismatch')
  ss,sa,sr=inspect(source,rows,'source');ts,ta,tr=inspect(target,rows,'target')
  report.update({'validatedObjects':2234,'texture2D':2221,'cubemaps':13,'payloadSavingsBytes':619998464,'sourceAssetSHA256':sa,'sourceStreamSHA256':sr,'targetAssetSHA256':ta,'targetStreamSHA256':tr,'notes':'Savings is active compressed payload, not physical app disk reduction or measured runtime footprint. Unreferenced old tails remain untouched. Original normal decode format3/4 excluded. All source/target size,mip,colorSpace,sampler fields exact.'})
  for r in rows:
   check(ss[(r['sourceAsset'],r['sourcePathID'])]['m_CompleteImageSize']>0,'Missing original complete-image size')
   report['changes'].append({'asset':r['targetAsset'],'pathID':r['targetPathID'],'name':r['name'],'fromFormat':r['targetFormat'],'toFormat':r['sourceFormat'],'oldBytes':r['targetBytes'],'newBytes':r['sourceBytes'],'sha256':r['sourcePayloadSHA256']})
  report['inputDataUnchanged']=True;report['status']='plan-verified'
  if not a.apply:write_report(report_path,report);print('PLAN PASS 2234 original payload/meta checks; no Data writes');return
  check(a.output_data is not None and a.validated_sample_report is not None,'Apply requires --output-data and --validated-sample-report')
  dest=a.output_data.resolve();private_output(dest,source,target)
  check(not dest.exists() and not inside(source,dest) and not inside(target,dest),'Requires fresh non-overlapping output Data directory')
  report['validatedSampleReportSHA256']=verify_sample(a.validated_sample_report.resolve())
  # All selected source/target files stay unchanged throughout the operation.
  for root,hashes in [(source,{**sa,**sr}),(target,{**ta,**tr})]:
   for f,h in hashes.items():check(digest(root/f)==h,'Input changed during plan: '+f)
  dest.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['cp','-cR',str(target),str(dest)],check=True)
  for f,h in {**ta,**tr}.items():check(digest(dest/f)==h,'Clone differs before patch '+f)
  grouped=collections.defaultdict(list)
  for row in rows:grouped[row['targetAsset']].append(row)
  for filename,items in grouped.items():
   env=load_asset(dest,filename);asset=env.file;before={o.path_id:digest_bytes(o.get_raw_data())for o in env.objects};refs=references(asset);expected={}
   for r in items:
    pid=r['targetPathID'];s=ss[(r['sourceAsset'],r['sourcePathID'])];t=copy.deepcopy(ts[(filename,pid)]);stream=r['sourceStream'];dst=r['targetStream']
    with (source/stream['path']).open('rb')as f:f.seek(stream['offset']);raw=f.read(stream['size'])
    check(digest_bytes(raw)==r['sourcePayloadSHA256'],'Source changed before write')
    with (dest/dst['path']).open('r+b')as f:f.seek(dst['offset']);f.write(raw)
    t['m_TextureFormat']=s['m_TextureFormat'];t['m_CompleteImageSize']=s['m_CompleteImageSize'];t['m_StreamData']['size']=stream['size']
    check(t['m_IsReadable'] is False,'Readability unexpectedly changed');expected[pid]=t;asset.objects[pid].save_typetree(t)
   data=asset.save();(dest/filename).write_bytes(data);del data,env;gc.collect()
   after=load_asset(dest,filename);check(set(after.file.objects)==set(before),'Object IDs changed');check(references(after.file)==refs,'Asset external/script references changed')
   for obj in after.objects:
    if obj.path_id in expected:check(obj.read_typetree()==expected[obj.path_id],'Selected object changed outside exact3fields')
    else:check(digest_bytes(obj.get_raw_data())==before[obj.path_id],'Unselected object bytes changed')
   del after;gc.collect();print(filename,len(items),'objects restored and verified',flush=True)
  # Prove output streams differ only inside the ORIGINAL payload prefix of selected slots.
  ranges=collections.defaultdict(list)
  for r in rows:ranges[r['targetStream']['path']].append((r['targetStream']['offset'],r['sourceBytes'],r['sourcePayloadSHA256']))
  for stream,segments in ranges.items():
   segments.sort();cursor=0;length=(target/stream).stat().st_size;check((dest/stream).stat().st_size==length,'Stream file length changed')
   for offset,size,sha in segments:
    check(offset>=cursor,'Selected stream ranges overlap');check(digest(target/stream,cursor,offset-cursor)==digest(dest/stream,cursor,offset-cursor),'Unrelated stream bytes changed')
    check(digest(dest/stream,offset,size)==sha,'Restored BC bytes changed');cursor=offset+size
   check(digest(target/stream,cursor,length-cursor)==digest(dest/stream,cursor,length-cursor),'Trailing stream bytes changed')
  for root,hashes in [(source,{**sa,**sr}),(target,{**ta,**tr})]:
   for f,h in hashes.items():check(digest(root/f)==h,'Input file changed '+f)
  report.update({'status':'restored-byte-verified','outputData':str(dest),'inputDataUnchanged':True,'signed':False,'runtimeVerified':False})
  write_report(report_path,report);print('APPLY byte verification PASS; new private Data only, requires package signing and runtime acceptance')
 except Exception as e:
  report.update({'status':'failed','error':str(e)});write_report(report_path,report);raise

def digest_bytes(data):return hashlib.sha256(data).hexdigest()
if __name__=='__main__':main()
