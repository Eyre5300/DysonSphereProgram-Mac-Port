import os
from pathlib import Path
import json,struct,hashlib,UnityPy,lz4.block
root=Path(os.environ['DSP_GAME_INPUT'])/'DSPGAME_Data'
out=Path('work/dsp-runtime/graphics-metadata');out.mkdir(exist_ok=True);records=[]
for filename in ['resources.assets','sharedassets0.assets','globalgamemanagers.assets']:
 env=UnityPy.load(str(root/filename))
 for obj in env.objects:
  if obj.type.name!='Shader':continue
  d=obj.parse_as_object();meta=obj.read_typetree();meta.pop('compressedBlob',None);mapping={}
  for platform,offsets,clens,dlens in zip(d.platforms,d.offsets,d.compressedLengths,d.decompressedLengths):
   if platform!=4:continue
   raws=[lz4.block.decompress(bytes(d.compressedBlob)[o:o+c],uncompressed_size=n)for o,c,n in zip(offsets,clens,dlens)]
   count=struct.unpack_from('<I',raws[0])[0]
   for n in range(count):
    off,size,seg=struct.unpack_from('<III',raws[0],4+12*n);chunk=raws[seg][off:off+size];idx=chunk.find(b'DXBC')
    if idx<0:continue
    length=struct.unpack_from('<I',chunk,idx+24)[0];code=chunk[idx:idx+length];mapping[n]=hashlib.sha256(code).hexdigest()
  meta['program_mapping']=mapping;path=out/(str(obj.path_id)+'-'+filename+'.json');path.write_text(json.dumps(meta))
  records.append(dict(name=d.m_ParsedForm.m_Name,path=str(path)))
 print(filename,len(records),flush=True)
(out/'index.json').write_text(json.dumps(records,indent=2))
