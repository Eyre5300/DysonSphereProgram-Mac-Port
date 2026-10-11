import os
from pathlib import Path
import json,struct,hashlib,UnityPy,lz4.block
root=Path(os.environ['DSP_GAME_INPUT'])/'DSPGAME_Data'
out=Path('work/dsp-runtime/graphics-parameters');out.mkdir(exist_ok=True)
for filename in ['resources.assets','sharedassets0.assets','globalgamemanagers.assets']:
 env=UnityPy.load(str(root/filename))
 for obj in env.objects:
  if obj.type.name!='Shader':continue
  d=obj.parse_as_object()
  for platform,offsets,clens,dlens in zip(d.platforms,d.offsets,d.compressedLengths,d.decompressedLengths):
   if platform!=4:continue
   raws=[lz4.block.decompress(bytes(d.compressedBlob)[o:o+c],uncompressed_size=n)for o,c,n in zip(offsets,clens,dlens)]
   count=struct.unpack_from('<I',raws[0])[0]
   for n in range(count):
    off,size,seg=struct.unpack_from('<III',raws[0],4+12*n);chunk=raws[seg][off:off+size]
    if b'DXBC' not in chunk:(out/(str(obj.path_id)+'-'+filename+'-'+str(n)+'.bin')).write_bytes(chunk)
 print(filename,flush=True)
