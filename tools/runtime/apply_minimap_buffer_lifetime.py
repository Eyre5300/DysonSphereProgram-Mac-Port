"""Keep original minimap data/layout, defer only Mac GPU buffer disposal."""
import argparse
from pathlib import Path

def apply(project):
    path=Path(project)/'Assets/Scripts/Assembly-CSharp/MiniBlockContainer.cs'
    text=path.read_text()
    if text.count('PortMiniBlockBuffers.Retire(')==3:
        if 'computeBuffer.Release();' in text or 'argBuffer.Release();' in text:
            raise ValueError('Mixed minimap disposal state; refusing to patch')
        return
    if text.count('computeBuffer.Release();')!=2 or text.count('argBuffer.Release();')!=1:
        raise ValueError('Unsupported minimap disposal layout; original version must be checked')
    text=text.replace('computeBuffer.Release();','PortMiniBlockBuffers.Retire(computeBuffer);')
    text=text.replace('argBuffer.Release();','PortMiniBlockBuffers.Retire(argBuffer);')
    path.write_text(text)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    apply(parser.parse_args().project)
