"""Lower the original shell point/geometry pipeline to indexed triangles for Metal.

Keep the original geometry and fragment arithmetic. Each duplicated input point
selects one of the twelve emitted vertices; CPU indices reproduce three strips.
"""
from pathlib import Path
import json, re

ns = {}
exec(Path('work/dsp-runtime/recover_graphics.py').read_text().split('records=[];failures=[]')[0], ns)
root = Path('work/dsp-runtime')
meta = json.loads((root/'graphics-metadata/10116-resources.assets.json').read_text())
pa = meta['m_ParsedForm']['m_SubShaders'][0]['m_Passes'][0]
def recover(stage):
    p = pa[stage]
    sub, pi = next((s, i) for group, ids in zip(p['m_PlayerSubPrograms'], p['m_ParameterBlobIndices']) for s, i in zip(group, ids))
    return ns['rebuild_stage'](meta, pa, stage, sub, '10116-resources.assets-'+str(pi)+'.bin')[0]

geom = recover('progGeometry')
# The original vertex stage passes POSITION.xyz, UV0/UV1 and UV2 unchanged.
geom = re.sub(r'\[maxvertexcount\(12\)\].*', '', geom, flags=re.S)
geom = geom.replace('void geom_main(point SPIRV_Cross_Input stage_input[1], inout TriangleStream<SPIRV_Cross_Output> geometry_stream)',
                    'SPIRV_Cross_Output ShellVertex(uint corner)')
geom = geom.replace('geometry_stream.RestartStrip();', '')
counter = [0]
def emit(m):
    n = counter[0]; counter[0] += 1
    return f'if (corner == {n}u) return stage_output;'
geom = re.sub(r'geometry_stream.Append\(stage_output\);', emit, geom)
assert counter[0] == 12
last = geom.rfind('}')
geom = geom[:last] + '\n    SPIRV_Cross_Output clipped = (SPIRV_Cross_Output)0;\n    clipped.gl_Position = float4(2,2,2,1);\n    return clipped;\n' + geom[last:]
geom += '''
struct ShellMeshInput {
 float4 position : POSITION;
 float2 uv : TEXCOORD0;
 float2 uv2 : TEXCOORD1;
 float2 uv3 : TEXCOORD2;
 float2 corner : TEXCOORD3;
};
SPIRV_Cross_Output RecoveredVert(ShellMeshInput input) {
 v0[0] = input.position.xyz;
 v1[0] = float4(input.uv, input.uv2);
 v2[0] = input.uv3;
 return ShellVertex((uint)input.corner.x);
}
'''
frag = recover('progFragment')
name = 'VF Shaders/Dyson Sphere/Dyson Shell Unlit'
header = ns['shaderpaths'][name][0][1]
text = header + '\nSubShader { Tags { "RenderType"="DysonShell" }\nPass {\n' + ns['state'](pa) + '''
HLSLPROGRAM
#pragma target 5.0
#pragma vertex RecoveredVert
#pragma fragment RecoveredFrag
#if defined(SHADER_STAGE_VERTEX)
''' + geom + '\n#endif\n#if defined(SHADER_STAGE_FRAGMENT)\n' + frag + '\n#endif\nENDHLSL\n}\n}\nFallback Off\n}\n'
for path in [root/'preflight-project/Assets/RecoveredGraphics/MetalDysonShell.shader',
             root/'port-project/Assets/Resources/dyson sphere/shaders/dyson shell unlit.shader']:
    path.write_text(text)
print('Recovered shell geometry as 12 vertices / 6 triangles per cell')
