"""Restore original tessellation arithmetic and adaptive factors for Metal.
SPIRV-Cross cannot emit HLSL tessellation, so translate this small GLSL domain
stage, then use the existing reflection-based uniform reconstruction.
"""
from pathlib import Path
import re,json,subprocess
root=Path('work/dsp-runtime');ns={}
exec((root/'recover_graphics.py').read_text().split('records=[];failures=[]')[0],ns)
meta=json.loads((root/'graphics-metadata/9963-resources.assets.json').read_text());pa=meta['m_ParsedForm']['m_SubShaders'][0]['m_Passes'][1]
def entry(stage):
 p=pa[stage];return next((s,i) for g,ids in zip(p['m_PlayerSubPrograms'],p['m_ParameterBlobIndices']) for s,i in zip(g,ids))
def recover(stage):
 s,i=entry(stage);return ns['rebuild_stage'](meta,pa,stage,s,'9963-resources.assets-'+str(i)+'.bin')[0]
vert=recover('progVertex');frag=recover('progFragment')
# Prefix stage-local symbols; uniforms retain exact names.
def prefix(code,tag):
 ids=set(re.findall(r'\b(?:Read_\w+|r\d+|v\d+|o\d+|SPIRV_Cross_\w+|gl_PointSize|vert_main)\b',code))
 return re.sub(r'\b('+ '|'.join(sorted(ids,key=len,reverse=True))+r')\b',lambda m:tag+m[0],code)
vert=prefix(vert,'VS_')
# Domain operations remain in the order emitted from the original SPIR-V.
glsl=(root/'painting-domain.glsl').read_text()
glsl=re.sub(r'^#version.*\n|^layout\(triangles\) in;\n','',glsl,flags=re.M)
def cb(m):return 'cbuffer cb'+m[1]+' : register(b'+m[1]+') { float4 cb'+m[1]+'_'+m[1]+'_m0['+m[2]+'] : packoffset(c0); };'
glsl=re.sub(r'layout\(binding = (\d+), std140\) uniform \w+\s*\{\s*vec4 _m0\[(\d+)\];\s*\} \w+;',cb,glsl)
glsl=re.sub(r'cb(\d+)_\d+\._m0',lambda m:'cb'+m[1]+'_'+m[1]+'_m0',glsl)
glsl=glsl.replace('layout(location = 0) in vec4 v0[];','static float4 v0[3];\nstatic float3 gl_TessCoord;\nstatic float4 gl_Position;').replace('layout(location = 1) out vec4 o1;','static float4 o1;')
for a,b in [('uvec','uint'),('vec','float'),('uintBitsToFloat','asfloat'),('floatBitsToUint','asuint'),('inversesqrt','rsqrt'),('fma','mad'),('notEqual','PortNotEqual'),('mix','PortSelect')]:glsl=glsl.replace(a,b)
glsl=re.sub(r'float([234])\(([-+\d.e]+)\)',lambda m:'((float'+m[1]+')'+m[2]+')',glsl)
glsl=re.sub(r'uint([234])\(0u\)',lambda m:'((uint'+m[1]+')0u)',glsl)
glsl=re.sub(r'^float4 (r\d+);',r'static float4 \1;',glsl,flags=re.M)
glsl=glsl.replace('void main()', 'void DomainArithmetic()')
sha=meta['program_mapping'][str(entry('progDomain')[0]['m_BlobIndex'])]
cache=root/'painting-hlsl';cache.mkdir(exist_ok=True);(cache/(sha+'.hlsl')).write_text(glsl)
oldcache=ns['cache'];ns['cache']=cache
domain=recover('progDomain');ns['cache']=oldcache
domain=prefix(domain,'DS_')
# Share each uniform declaration across vertex and domain stages.
seen=set()
def decls(code):
 def one(m):
  s=m[0]
  if s in seen:return ''
  seen.add(s);return s
 return re.sub(r'^(?:float|int|uint)(?:[234](?:x[234])?)? [A-Za-z_]\w*(?:\[\d+\])?;$',one,code,flags=re.M)
vert=decls(vert);domain=decls(domain)
helpers='\n'.join('bool'+str(n)+' PortNotEqual(uint'+str(n)+' a,uint'+str(n)+' b){return a!=b;}\nfloat'+str(n)+' PortSelect(float'+str(n)+' a,float'+str(n)+' b,bool'+str(n)+' c){return c?b:a;}' for n in [2,3,4])
wrappers='''
struct TessFactors { float edge[3] : SV_TessFactor; float inside : SV_InsideTessFactor; };
TessFactors PatchConstants(InputPatch<VS_SPIRV_Cross_Output,3> patch) {
 // Original hull join(): tessellate to 3 near the camera, otherwise 1.
 float radius = _Global_DS_RenderPlace == 0 ? _OrbitRadius : _OrbitRadius * 0.00025000001187436282634735107421875;
 float averageDistance = (patch[0].VS_o1 + patch[1].VS_o1 + patch[2].VS_o1) * 0.3333333432674407958984375;
 float factor = averageDistance < radius * 0.0500000007450580596923828125 ? 3.0 : 1.0;
 TessFactors output; output.edge[0]=output.edge[1]=output.edge[2]=output.inside=factor; return output;
}
[domain("tri")][partitioning("fractional_odd")][outputtopology("triangle_cw")]
[outputcontrolpoints(3)][patchconstantfunc("PatchConstants")]
VS_SPIRV_Cross_Output RecoveredHull(InputPatch<VS_SPIRV_Cross_Output,3> patch,uint id:SV_OutputControlPointID){return patch[id];}
struct DomainOutput {float4 position:SV_Position;float4 screen:TEXCOORD1;};
[domain("tri")]
DomainOutput RecoveredDomain(TessFactors factors,const OutputPatch<VS_SPIRV_Cross_Output,3> patch,float3 bary:SV_DomainLocation){
 DS_v0[0]=patch[0].VS_o0;DS_v0[1]=patch[1].VS_o0;DS_v0[2]=patch[2].VS_o0;
 gl_TessCoord=bary;DomainArithmetic();DomainOutput output;output.position=gl_Position;output.screen=DS_o1;return output;
}
'''
frag=frag.replace('_Color32Buffer.Load(', 'PortRead_Color32Buffer(').replace('Buffer<uint4> _Color32Buffer;', 'Buffer<uint4> _Color32Buffer;\nuint _PortWords_Color32Buffer;\nuint4 PortRead_Color32Buffer(uint index){return index<_PortWords_Color32Buffer?_Color32Buffer.Load(index):uint4(0,0,0,0);}')
name='VF Shaders/Dyson Sphere/Dyson Layer Painting Overlay';header=ns['shaderpaths'][name][0][1]
text=header+'\nSubShader { Tags { "Queue"="Transparent" }\nGrabPass { "_ScreenTex_Painting" }\nPass {\n'+ns['state'](pa)+'''
HLSLPROGRAM
#pragma target 5.0
#pragma skip_optimizations metal
#pragma vertex RecoveredVert
#pragma hull RecoveredHull
#pragma domain RecoveredDomain
#pragma fragment RecoveredFrag
#if !defined(SHADER_STAGE_FRAGMENT)
'''+helpers+'\n'+vert+'\n'+domain+'\n'+wrappers+'\n#else\n'+frag+'\n#endif\nENDHLSL\n}\n}\nFallback Off\n}\n'
path=root/'preflight-project/Assets/RecoveredGraphics/MetalPainting.shader';path.write_text(text)
(root/'painting-tessellation-recovered.shader').write_text(text)
print(path)
