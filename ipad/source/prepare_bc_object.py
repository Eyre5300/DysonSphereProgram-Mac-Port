"""Create a private candidate object; original library and instruction bytes unchanged.
Rename seven definitions, append undefined wrapper symbols, redirect call relocations to wrappers (including intra-object callers).
Unwind/debug/address identity references keep the original implementation. Caller links authored shim.
"""
from pathlib import Path
import struct,json,hashlib
import argparse
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();p=a.work.resolve();src=p/'TextureFormatMetal_y0zou.o';b=bytearray(src.read_bytes());assert struct.unpack_from('<I',b)[0]==0xfeedfacf
assert hashlib.sha256(b).hexdigest()=='ab96703e3d21c569888ca79543b93226a7dd49f7bb2cca960b10ef1b22fd6b3b', 'Unexpected Unity object version; stop rather than apply unverified offsets'
names={'__ZN5metal11PixelFormatE14GraphicsFormatPS0_':'_DSPBCOriginalPixelFormat','__ZN5metal19UnityGraphicsFormatE14MTLPixelFormat':'_DSPBCOriginalUnityGraphicsFormat','__ZN5metal20InitFormatUsageFlagsEP12GraphicsCaps':'_DSPBCOriginalInitFormatUsageFlags','__ZN5metal22PixelFormatElementSizeE14MTLPixelFormat':'_DSPBCOriginalPixelFormatElementSize','__ZN5metal22TextureFormatBlockSizeE14MTLPixelFormat':'_DSPBCOriginalTextureFormatBlockSize','__ZN5metal23IsCompressedPixelFormatE14MTLPixelFormat':'_DSPBCOriginalIsCompressedPixelFormat','__ZN5metal23IsTextureViewCompatibleE14MTLPixelFormatS0_':'_DSPBCOriginalIsTextureViewCompatible'}
o=32;sections=[]
for _ in range(struct.unpack_from('<I',b,16)[0]):
 c,z=struct.unpack_from('<II',b,o)
 if c==0x19:
  for i in range(struct.unpack_from('<I',b,o+64)[0]):
   s=o+72+i*80;name=bytes(b[s:s+16]).split(b'\0')[0].decode();offset=struct.unpack_from('<I',b,s+48)[0];size=struct.unpack_from('<Q',b,s+40)[0];rel,count=struct.unpack_from('<II',b,s+56);sections.append((name,offset,size,rel,count))
 if c==2:sc=o;symoff,nsyms,stroff,strsize=struct.unpack_from('<IIII',b,o+8)
 if c==0xb:dc=o
 o+=z
strings=bytearray(b[stroff:stroff+strsize]);entries=[bytearray(b[symoff+i*16:symoff+(i+1)*16]) for i in range(nsyms)];redirect={};matched=[]
for i,e in enumerate(entries[:]):
 off=struct.unpack_from('<I',e)[0];name=bytes(strings[off:]).split(b'\0')[0].decode()
 if name not in names:continue
 assert e[4]&0xe==0xe and e[4]&1
 alias=names[name];newstr=len(strings);strings.extend(alias.encode()+b'\0');struct.pack_into('<I',e,0,newstr)
 redirect[i]=len(entries);entries.append(bytearray(struct.pack('<IBBHQ',off,1,0,0,0)));matched.append({'original':name,'alias':alias,'definitionIndex':i,'wrapperIndex':redirect[i]})
assert len(matched)==7
rewrites=[]
for section,_,_,rel,count in sections:
 for i in range(count):
  addr,bits=struct.unpack_from('<II',b,rel+i*8)
  if section=='__text' and (bits>>28)==2 and bits&(1<<27) and (bits&0xffffff) in redirect:
   old=bits&0xffffff;new=redirect[old];struct.pack_into('<I',b,rel+i*8+4,(bits&0xff000000)|new);rewrites.append({'section':section,'address':addr,'old':old,'new':new})
assert len(rewrites)==7, 'Unexpected call relocations; audit this object again'
# Keep all EH/debug/non-call relocation bytes exactly unchanged.
originalRelocBytes=src.read_bytes()
for section,_,_,rel,count in sections:
 if section!='__text':assert b[rel:rel+count*8]==originalRelocBytes[rel:rel+count*8]
while len(b)%8:b.append(0)
newsyms=len(b);b.extend(b''.join(entries));newstrings=len(b);b.extend(strings);struct.pack_into('<IIII',b,sc+8,newsyms,len(entries),newstrings,len(strings));oldcount=struct.unpack_from('<I',b,dc+28)[0];struct.pack_into('<I',b,dc+28,oldcount+7)
original=src.read_bytes();text=next(x for x in sections if x[0]=='__text');_,offset,size,_,_=text;assert b[offset:offset+size]==original[offset:offset+size]
(p/'TextureFormatMetal_bc_candidate.o').write_bytes(b);report={'originalObjectSHA256':hashlib.sha256(original).hexdigest(),'candidateObjectSHA256':hashlib.sha256(b).hexdigest(),'arm64TextSHA256':hashlib.sha256(b[offset:offset+size]).hexdigest(),'instructionsUnchanged':True,'definitions':matched,'relocationsRedirected':rewrites};(p/'candidate-object-receipt.json').write_text(json.dumps(report,indent=2));print('Renamed7 definitions; redirected',len(rewrites),'relocations; __text exact.')
# Separate host test object; candidate iOS object above is preserved.
o=32
for _ in range(struct.unpack_from('<I',b,16)[0]):
 c,z=struct.unpack_from('<II',b,o)
 if c==0x32:struct.pack_into('<III',b,o+8,1,14<<16,14<<16)
 o+=z
(p/'TextureFormatMetal_bc_candidate_host.o').write_bytes(b)
