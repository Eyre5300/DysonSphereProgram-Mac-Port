"""Restore D3D null-read semantics for recovered read-only shader buffers.

Metal requires every declared buffer to be bound, even when the current material
does not use the associated feature. Use a zero buffer as the global default;
normal game SetBuffer calls override it. Bounds checks make the small default
safe for all indices instead of relying on out-of-bounds GPU reads.
"""
from pathlib import Path
import json,re
root=Path('work/dsp-runtime')
names=set(); changed=[]
# Variants generated later keep their guards in includes; their C# bindings
# must also receive word counts, otherwise valid models read zero-length data.
for include in (root/'port-project/Assets').rglob('*.hlsl'):
    names.update(re.findall(r'Buffer<uint4> (\w+);', include.read_text()))
for p in (root/'port-project/Assets').rglob('*.shader'):
    text=p.read_text()
    buffers=set(re.findall(r'Buffer<uint4> (\w+);',text))
    names.update(buffers)
    if not buffers:continue
    for name in sorted(buffers):
        helper='PortRead'+name
        decl=f'Buffer<uint4> {name};'
        # Unity 2022's Metal compiler cannot query buffer sizes in shaders.
        # The paired C# binding adapter supplies the actual raw word count.
        text=re.sub(r'\nuint _PortWords'+re.escape(name)+r';', '', text)
        text=re.sub(r'\nuint4 '+re.escape(helper)+r'\(uint \w+\)\s*\{[^\n]+\}', '', text)
        text=text.replace(name+'.Load(',helper+'(')
        code=decl+f'\nuint _PortWords{name};\nuint4 {helper}(uint index) {{ return index < _PortWords{name} ? {name}.Load(index) : uint4(0,0,0,0); }}'
        text=text.replace(decl,code)
    if '// DSP_METAL_BUFFER_SAFETY' not in text:text+='\n// DSP_METAL_BUFFER_SAFETY\n'
    p.write_text(text);changed.append(str(p))
quoted=',\n   '.join(json.dumps(n) for n in sorted(names))
source='''using UnityEngine;
using System.Collections.Generic;
public static class PortMetalBuffers {
 static ComputeBuffer zero;
 static readonly Dictionary<int,int> lengths=new Dictionary<int,int>();
 static readonly string[] names=new string[]{
   '''+quoted+'''
 };
 static void Ensure(){if(zero!=null)return;
  zero=new ComputeBuffer(16,4);zero.SetData(new uint[16]);
  foreach(string name in names)lengths[Shader.PropertyToID(name)]=Shader.PropertyToID("_PortWords"+name);
 }
 static int Words(ComputeBuffer buffer){return buffer==null?0:buffer.count*(buffer.stride/4);}
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterAssembliesLoaded)]
 static void Install(){
  Ensure();
  // Real material and global bindings subsequently replace these defaults.
  foreach(string name in names)SetGlobalBuffer(name,null);
  Application.quitting+=Release;
 }
 public static void SetGlobalBuffer(string name,ComputeBuffer buffer){SetGlobalBuffer(Shader.PropertyToID(name),buffer);}
 public static void SetGlobalBuffer(int name,ComputeBuffer buffer){Ensure();Shader.SetGlobalBuffer(name,buffer??zero);if(lengths.TryGetValue(name,out int id))Shader.SetGlobalInt(id,Words(buffer));}
 public static void PortSetBuffer(this Material mat,string name,ComputeBuffer buffer){PortSetBuffer(mat,Shader.PropertyToID(name),buffer);}
 public static void PortSetBuffer(this Material mat,int name,ComputeBuffer buffer){Ensure();mat.SetBuffer(name,buffer??zero);if(lengths.TryGetValue(name,out int id))mat.SetInt(id,Words(buffer));}
 public static void PortSetBuffer(this MaterialPropertyBlock mat,string name,ComputeBuffer buffer){PortSetBuffer(mat,Shader.PropertyToID(name),buffer);}
 public static void PortSetBuffer(this MaterialPropertyBlock mat,int name,ComputeBuffer buffer){Ensure();mat.SetBuffer(name,buffer??zero);if(lengths.TryGetValue(name,out int id))mat.SetInt(id,Words(buffer));}
 // Compute shaders keep their original bindings and layout.
 public static void PortSetBuffer(this ComputeShader shader,int kernel,string name,ComputeBuffer buffer){shader.SetBuffer(kernel,name,buffer);}
 public static void PortSetBuffer(this ComputeShader shader,int kernel,int name,ComputeBuffer buffer){shader.SetBuffer(kernel,name,buffer);}
 static void Release(){if(zero!=null){zero.Release();zero=null;}}
}
'''
(root/'port-project/Assets/PortMetalBuffers.cs').write_text(source)
for p in (root/'port-project/Assets/Scripts/Assembly-CSharp').rglob('*.cs'):
    text=p.read_text();updated=text.replace('Shader.SetGlobalBuffer(', 'PortMetalBuffers.SetGlobalBuffer(').replace('.SetBuffer(', '.PortSetBuffer(')
    if updated!=text:p.write_text(updated)
(root/'metal-buffer-safety.json').write_text(json.dumps(dict(buffers=sorted(names),changed=changed),indent=2))
print(len(changed),'shaders guarded;',len(names),'global null-buffer defaults')
