from pathlib import Path
import re,struct

def splitargs(s):
 out=[];depth=0;start=0
 for i,c in enumerate(s):
  if c=='(':depth+=1
  elif c==')':depth-=1
  elif c==',' and depth==0:out.append(s[start:i].strip());start=i+1
 out.append(s[start:].strip());return out

def call(s):
 m=re.match(r'^(\w+)\(',s)
 if not m or not s.endswith(')'):return None
 depth=0
 for i in range(m.end()-1,len(s)):
  depth += (s[i]=='(')-(s[i]==')')
  if depth==0 and i!=len(s)-1:return None
 return m[1],s[m.end():-1]

def bits(expr):
 expr=expr.strip();c=call(expr)
 if c and c[0]=='asfloat':return 'asuint('+c[1]+')'
 if c and re.fullmatch(r'float[234]',c[0]) and len(splitargs(c[1]))>1:
  return 'uint'+c[0][-1]+'('+','.join(bits(a) for a in splitargs(c[1]))+')'
 if re.fullmatch(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?f?',expr):
  return '0x%08xu'%struct.unpack('<I',struct.pack('<f',float(expr.rstrip('f'))))[0]
 return 'asuint('+expr+')'

def simplify(s):
 # Cancel nested bitcasts explicitly, before the Unity compiler can fold subnormals.
 for _ in range(10):
  old=s
  for m in list(re.finditer(r'\bas(uint|int)\(asfloat\(',s))[::-1]:
   innerstart=m.end();d=1;j=innerstart
   while j<len(s) and d:
    d+=(s[j]=='(')-(s[j]==')');j+=1
   if j<len(s) and s[j]==')':s=s[:m.start()]+'as'+m[1]+'('+s[innerstart:j-1]+')'+s[j+1:]
  s=re.sub(r'asuint\((port_(?:r\d+|_\d+)(?:\.[xyzw]+)?)\)',r'\1',s)
  s=re.sub(r'asuint\((0x[0-9a-f]+u|\d+u)\)',r'\1',s)
  if s==old:break
 return s

def transform_block(s):
 regs=set(re.findall(r'static float[234]? (r\d+);',s)) | set(re.findall(r'\bfloat[234]? (_\d+) =',s))
 out=[]
 for line in s.splitlines():
  if re.match(r'static float[234]? r\d+;',line):out.append(re.sub(r'float([234]?) (r\d+)',r'uint\1 port_\2',line));continue
  decl=re.match(r'(\s*)float([234]?) (_\d+) = (.*);$',line)
  m=re.match(r'(\s*)((?:r\d+|_\d+)(?:\.[xyzw]+)?) (\+=|-=|\*=|/=|=) (.*);$',line)
  def read(t):return re.sub(r'\b(r\d+|_\d+)(\.[xyzw]+)?\b',lambda m:'asfloat(port_'+m[1]+(m[2] or '')+')' if m[1] in regs else m[0],t)
  if decl:
   out.append(decl[1]+'uint'+decl[2]+' port_'+decl[3]+' = '+simplify(bits(read(decl[4])))+';');continue
  if m and m[2].split('.')[0] in regs:
   rhs=read(m[4]);op=m[3]
   if op!='=':rhs=read(m[2])+' '+op[0]+' ('+rhs+')'
   out.append(m[1]+'port_'+m[2]+' = '+simplify(bits(rhs))+';')
  else:out.append(simplify(read(line)))
 return '\n'.join(out)+'\n'
def transform(s):
 # Temporary IDs are local to each separately recovered shader variant.
 parts=re.split(r'(?m)(^#(?:if|elif|else|endif)[^\n]*\n)',s)
 return ''.join(p if p.startswith('#') else transform_block(p) for p in parts)

if __name__=='__main__':
 p=Path('work/dsp-runtime/preflight-project/Assets/Resources/FormationAudit')
 (p/'LancerTyped.compute').write_text(transform((p/'LancerDefault.compute').read_text()))
 f=Path('work/dsp-runtime/preflight-project/Assets/Editor/PortFormationAudit.cs')
 s=f.read_text().replace('"LancerLiteralsSafe"}','"LancerLiteralsSafe","LancerTyped"}');f.write_text(s)
