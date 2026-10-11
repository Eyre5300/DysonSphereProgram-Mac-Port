import re

def split_args(args):
 depth=0
 for i,c in enumerate(args):
  if c=='(':depth+=1
  elif c==')':depth-=1
  elif c==',' and depth==0:return args[:i],args[i+1:].strip()
 raise AssertionError('Missing store argument separator')

def restore_append_buffers(text,names):
 for counter in re.findall(r'RWByteAddressBuffer (u\d+_\d+);',text):
  target=names[counter.split('_')[0]];pattern=r'uint (\w+);\s*'+re.escape(counter)+r'\.InterlockedAdd\(0, 1, \1\);\s*(r\d+\.[xyzw]) = asfloat\(\1\);';allocs=list(re.finditer(pattern,text));assert allocs,counter;strides=set()
  for alloc in reversed(allocs):
   # Every D3D append allocation and its stores are in one lexical block.
   start=alloc.end();i=start;depth=0
   while i<len(text):
    if text[i]=='{':depth+=1
    elif text[i]=='}':
     if depth==0:break
     depth-=1
    i+=1
   body=text[start:i];stores=list(re.finditer(re.escape(target)+r'\.Store([234]?)\(([^\n]+)\);',body));assert stores,(target,'no stores')
   ns=set(int(x)for x in re.findall(r'uint\(asint\('+re.escape(alloc[2])+r'\)\) \* (\d+)u',body));assert len(ns)==1,(target,ns);n=ns.pop();strides.add(n)
   typ='AppendElement'+counter;temp='appendValue'+alloc[1]
   last=stores[-1].end();body=body[:last]+'\n'+target+'.Append('+temp+');'+body[last:]
   for si,m in reversed(list(enumerate(stores))):
    width=int(m[1]or'1');address,value=split_args(m[2]);v='appendWords'+alloc[1]+'_'+str(si);code='uint'+(str(width)if width>1 else'')+' '+v+' = '+value+';\n'
    for k in range(width):code+=temp+'.words[((('+address+')/4u)%'+str(n)+'u)+'+str(k)+'u] = '+v+('.'+'xyzw'[k]if width>1 else'')+';\n'
    body=body[:m.start()]+code+body[m.end():]
   allocation='uint '+alloc[1]+' = 0u;\n'+typ+' '+temp+';\n'+alloc[2]+' = asfloat('+alloc[1]+');'
   text=text[:alloc.start()]+allocation+body+text[i:]
  assert len(strides)==1,(target,strides);n=strides.pop();typ='AppendElement'+counter
  text=text.replace('RWByteAddressBuffer '+counter+';','')
  text=re.sub(r'RWByteAddressBuffer '+re.escape(target)+r'\s*:\s*register\(u\d+\);',f'struct {typ} {{ uint words[{n}]; }};\nAppendStructuredBuffer<{typ}> {target};',text)
  assert counter+'.InterlockedAdd' not in text
  assert target+'.Store'not in text
 return text
