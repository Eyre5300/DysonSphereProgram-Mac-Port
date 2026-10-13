"""Preserve mixed integer/float temporary bits in the iPad receiver-beam shader.

Device A/B: valid GPU animation data, original and depth-bypass invisible,
integer-register representation visible, original restored invisible again.
Keep shader conditions, textures, pass state and original numeric expressions.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
from private_paths import private_output
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools/runtime'))
from typed_register_probe import transform

MARKER='// DSP_IPAD_RAY_RECEIVER_REGISTER_BITS\n'
IDENTITY='Shader "VF Shaders/Forward/Unlit Additive Ray Receiver Gravity"'

def adapt(source):
    if source.count(IDENTITY)!=1:
        raise ValueError('Unexpected receiver shader identity')
    if source.startswith(MARKER):
        return source
    if source.count('void vert_main()')!=3 or source.count('void frag_main()')!=3:
        raise ValueError('Unexpected receiver variant layout')
    if 'Buffer<uint4> _AnimBuffer;' not in source or 'static float4 r0;' not in source:
        raise ValueError('Expected recovered receiver register representation')
    result=transform(source)
    if re.search(r'\bstatic float[234]? r\d+;', result):
        raise ValueError('Unconverted register declaration')
    # Variant interfaces, pass state and material/global binding declarations
    # are retained by the register transformation.
    return MARKER+result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    shader=private_output(a.project)/'Assets/Resources/shaders/vff unlit ray receiver gravity.shader'
    source=shader.read_text();result=adapt(source);shader.write_text(result)
    report=private_output(a.report);report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'scope':'iPad receiver gravity effect register representation only; original game state and render rules retained', 'changed':result!=source,'beforeSHA256':hashlib.sha256(source.encode()).hexdigest(),'afterSHA256':hashlib.sha256(result.encode()).hexdigest()},indent=2))

if __name__=='__main__':main()
