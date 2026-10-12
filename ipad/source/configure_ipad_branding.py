"""Derive private app icons from the user's original Windows executable.
Requires pefile and Pillow. No game icon is embedded in the public tools.
"""
import argparse, io, json, struct
from pathlib import Path
from private_paths import private_output

def configure(executable, catalog):
    import pefile
    from PIL import Image
    executable=Path(executable).resolve();catalog=private_output(catalog,[executable])
    pe=pefile.PE(str(executable));icons={};groups=[]
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id not in (3,14):continue
        for name in entry.directory.entries:
            data=name.directory.entries[0].data.struct
            blob=pe.get_data(data.OffsetToData,data.Size)
            if entry.id==3:icons[name.id]=blob
            else:groups.append(blob)
    if not groups:raise ValueError('Original executable has no icon group')
    group=groups[0];count=struct.unpack_from('<H',group,4)[0]
    headers=[];payload=[];offset=6+16*count
    for i in range(count):
        width,height,colors,reserved,planes,bits,size,key=struct.unpack_from('<BBBBHHIH',group,6+14*i)
        blob=icons[key];headers.append(struct.pack('<BBBBHHII',width,height,colors,reserved,planes,bits,len(blob),offset));payload.append(blob);offset+=len(blob)
    image=Image.open(io.BytesIO(struct.pack('<HHH',0,1,count)+b''.join(headers+payload)))
    original=image.ico.getimage(max(image.ico.sizes(),key=lambda s:s[0]*s[1])).convert('RGB')
    catalog.mkdir(parents=True,exist_ok=True);entries=[]
    for size,points,scale,idiom in [(76,'76x76','1x','ipad'),(152,'76x76','2x','ipad'),(167,'83.5x83.5','2x','ipad'),(1024,'1024x1024','1x','ios-marketing')]:
        filename='Icon-iPad-'+str(size)+'.png';original.resize((size,size),Image.Resampling.LANCZOS).save(catalog/filename)
        entries.append(dict(filename=filename,size=points,scale=scale,idiom=idiom))
    (catalog/'Contents.json').write_text(json.dumps({'images':entries,'info':{'author':'xcode','version':1}},indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);a=p.parse_args();configure(a.exe,a.catalog)
if __name__=='__main__':main()
