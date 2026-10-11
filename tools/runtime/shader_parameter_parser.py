import struct
class Reader:
 def __init__(self,b):self.b=b;self.p=0
 def u(self):v=struct.unpack_from('<I',self.b,self.p)[0];self.p+=4;return v
 def s(self):n=self.u();assert n<10000,(self.p,n);v=self.b[self.p:self.p+n].decode();self.p=(self.p+n+3)&~3;return v

def parse(b):
 r=Reader(b);version=r.u();assert version==202012090,version;cbs=[];bindings=[]
 for _ in range(r.u()):
  cb={'name':r.s(),'size':r.u(),'params':[]}
  for _ in range(r.u()):
   p={'name':r.s()};p.update(zip(['type','rows','cols','matrix','array','offset'],[r.u()for _ in range(6)]));cb['params'].append(p)
  structures=r.u();assert structures==0,('structs',structures)
  cbs.append(cb)
 for _ in range(r.u()):
  p={'name':r.s(),'type':r.u(),'index':r.u()}
  if p['type']==0:p['sampler']=r.u();p['dim']=r.u()
  elif p['type'] in [1,2,3,4]:p['extra']=r.u()
  else:raise ValueError(('bindingtype',p,r.p))
  bindings.append(p)
 assert r.p==len(b),(r.p,len(b))
 return dict(cbs=cbs,bindings=bindings)
if __name__=='__main__':
 from pathlib import Path
 import collections,json
 ok=0;errors=collections.Counter();types=collections.Counter();examples={};out={}
 for p in Path('work/dsp-runtime/graphics-parameters').glob('*.bin'):
  try:
   d=parse(p.read_bytes());ok+=1;out[p.name]=d
   for item in d['bindings']:types[item['type']]+=1;examples[item['type']]=item
  except Exception as e:errors[str(e)]+=1
 print('ok',ok,'errors',errors.most_common(12),'types',types,'examples',examples)
 Path('work/dsp-runtime/graphics-parameters/parsed.json').write_text(json.dumps(out))
