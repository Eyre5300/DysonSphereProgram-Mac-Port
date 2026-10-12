"""Preserve recovered power/sign vertex register bits during Metal compilation.

The normal compiler collapses quad-corner selectors represented as bitcast
float registers, making all four vertices coincide. Keep original shader
math, buffers, textures, blending and depth rules; change only compilation.
"""
import argparse
from pathlib import Path
from private_paths import private_output

NAMES = {
    'power disk batch.shader': 'Power Disk Batch',
    'power gendisk batch.shader': 'Power GenDisk Batch',
    'power conn batch.shader': 'Power Conn Batch',
    'entity sign batch.shader': 'Entity Sign Batch',
}
DIRECTIVE = '#pragma skip_optimizations metal'

def adapt(text, name):
    if ('Shader "VF Shaders/Batching/' + name + '"') not in text:
        raise ValueError('Unexpected shader identity: ' + name)
    if '#pragma vertex RecoveredVert' not in text or 'gl_VertexIndex' not in text or 'asfloat(' not in text:
        raise ValueError('Expected recovered procedural vertex program: ' + name)
    if DIRECTIVE in text:
        return text
    if text.count('#pragma target 5.0') != 1:
        raise ValueError('Unexpected shader pass layout: ' + name)
    return text.replace('#pragma target 5.0', '#pragma target 5.0\n' + DIRECTIVE, 1)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    root = private_output(args.project) / 'Assets/Resources/shaders'
    pending = {root / filename: adapt((root / filename).read_text(), name) for filename, name in NAMES.items()}
    for path, text in pending.items():
        path.write_text(text)

if __name__ == '__main__':
    main()
