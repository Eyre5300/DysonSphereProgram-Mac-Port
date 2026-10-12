from pathlib import Path
import json,hashlib,texture2ddecoder
import argparse
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--source-data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
manifest=json.loads(a.manifest.read_text());win=a.source_data.resolve();from private_paths import private_output
out=private_output(a.output,[win]);out.mkdir(parents=True,exist_ok=False)
names=['moon-inside-s','voxel-item-1110-0-paint-a','rounded-rect-grey-plaid','blend_ramp_0','bg-lgc','iris-text-18','voxel-item-1119-0-a','circle-tex-7','sci-fi-bracket-v','def_planet_env7','def_planet_env4','def_ice_env'];rows=[]
for i,name in enumerate(names):
 matches=[x for x in manifest['textures'] if x['name']==name];assert len(matches)==1;x=matches[0];m=x['metadata'];st=x['sourceStream'];
 with (win/st['path']).open('rb') as f:f.seek(st['offset']);raw=f.read(st['size'])
 assert hashlib.sha256(raw).hexdigest()==x['sourcePayloadSHA256'];filename=f'{i:02d}-format{x["sourceFormat"]}.bin';(out/filename).write_bytes(raw);bcsize=8 if x['sourceFormat']==10 else 16;w0,h0=m['m_Width'],m['m_Height'];offset=0;subresources=[]
 for face in range(m['m_ImageCount']):
  for level in range(m['m_MipCount']):
   w,h=max(1,w0>>level),max(1,h0>>level);size=((w+3)//4)*((h+3)//4)*bcsize;data=raw[offset:offset+size];assert len(data)==size;sample={'face':face,'level':level,'width':w,'height':h,'offset':offset,'bytes':size,'sha256':hashlib.sha256(data).hexdigest()}
   if x['sourceFormat']!=24:
    decode={10:texture2ddecoder.decode_bc1,12:texture2ddecoder.decode_bc3,25:texture2ddecoder.decode_bc7}[x['sourceFormat']];pixels=decode(data,w,h);coords=[(0,0),(w//2,h//2),(w-1,h-1)];golden=[]
    for px,py in coords:
     j=(py*w+px)*4;B,G,R,A=pixels[j:j+4];golden.append({'x':px,'y':py,'rgba8':[R,G,B,A]})
    sample['decodedBlockSamples']=golden;sample['alphaMinMax']=[min(pixels[3::4]),max(pixels[3::4])]
   subresources.append(sample);offset+=size
 assert offset==len(raw),(name,offset,len(raw));row={'name':name,'file':filename,'textureFormat':x['sourceFormat'],'type':m['type'],'width':w0,'height':h0,'mipCount':m['m_MipCount'],'imageCount':m['m_ImageCount'],'serializedColorSpace':m['m_ColorSpace'],'linearConstructor':m['m_ColorSpace']==0,'bytes':len(raw),'sha256':x['sourcePayloadSHA256'],'subresources':subresources,'sourceAsset':x['sourceAsset'],'sourcePathID':x['sourcePathID']};rows.append(row)
report={'source':'Exact original Windows compressed bytes; no encoding, no dimension/mip changes','decoder':'texture2ddecoder BC1/BC3/BC7 output BGRA byte order converted to RGBA; samples before sRGB transfer. BC6H intentionally no lossy8bit golden.','fixtures':rows};(out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Prepared',len(rows),'fixtures,',sum(x['bytes'] for x in rows),'bytes',sum(len(x['subresources']) for x in rows),'mip/face subresources')
