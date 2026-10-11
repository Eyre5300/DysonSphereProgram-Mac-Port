from pathlib import Path
import re,json
r=Path('work/dsp-runtime');ns={};exec((r/'recover_graphics.py').read_text().split('records=[];failures=[]')[0],ns)
m=json.loads((r/'graphics-metadata/6-globalgamemanagers.assets.json').read_text());pa=m['m_ParsedForm']['m_SubShaders'][18]['m_Passes'][0]
g=(r/'shell-depth-progGeometry.hlsl').read_text();g=re.sub(r'\[maxvertexcount\(12\)\].*','',g,flags=re.S)
g=g.replace('void geom_main(point SPIRV_Cross_Input stage_input[1], inout TriangleStream<SPIRV_Cross_Output> geometry_stream)','SPIRV_Cross_Output ShellDepthVertex(uint corner)').replace('geometry_stream.RestartStrip();','')
count=[0]
def emit(m):
 i=count[0];count[0]+=1;return f'if(corner=={i}u)return stage_output;'
g=re.sub(r'geometry_stream.Append\(stage_output\);',emit,g);assert count[0]==12
idx=g.rfind('}');g=g[:idx]+'\nSPIRV_Cross_Output clipped=(SPIRV_Cross_Output)0;clipped.gl_Position=float4(2,2,2,1);return clipped;\n'+g[idx:]
g+='''
struct ShellDepthInput {float4 position:POSITION;float4 normal:NORMAL;float2 corner:TEXCOORD3;};
SPIRV_Cross_Output RecoveredVert(ShellDepthInput input){
 gl_PositionIn[0]=input.position;v1[0]=input.position.xyz;v3[0]=input.normal;
 return ShellDepthVertex((uint)input.corner.x);
}
'''
sub='''SubShader { Tags { "RenderType"="DysonShell" } Pass {
'''+ns['state'](pa)+'''
HLSLPROGRAM
#pragma target 5.0
#pragma skip_optimizations metal
#pragma vertex RecoveredVert
#pragma fragment RecoveredFrag
#if defined(SHADER_STAGE_VERTEX)
'''+g+'\n#endif\n#if defined(SHADER_STAGE_FRAGMENT)\n'+(r/'shell-depth-progFragment.hlsl').read_text()+'\n#endif\nENDHLSL\n}\n}\n'
marker='// DSP_METAL_SHELL_DEPTH_BEGIN\n';end='// DSP_METAL_SHELL_DEPTH_END\n'
name='VF Overwrite/DepthNormalsTexture'
for original,_ in ns['shaderpaths'][name]:
 rel=original.relative_to(r/'recovered-project/ExportedProject');p=r/'port-project'/rel;s=p.read_text();s=re.sub(re.escape(marker)+'.*?'+re.escape(end),'',s,flags=re.S)
 i=s.rfind('Fallback Off');assert i>0;s=s[:i]+marker+sub+end+s[i:];p.write_text(s)
(r/'preflight-project/Assets/RecoveredGraphics/MetalShellDepth.shader').write_text('Shader "Port/ShellDepth" {\n'+sub+'}\n')
print('Shell depth-normal geometry restored on the existing 12-vertex triangles')
