"""Use transient MSAA storage only at the four validated Mac UI allocations."""
import argparse
from pathlib import Path

TARGETS = {'UIStarmap': ('starmapRT', 'gizmoRT'),
           'DysonMapCamera': ('screenRT',), 'MechaEditorCamera': ('screenRT',)}

def apply(project):
    base = Path(project) / 'Assets/Scripts/Assembly-CSharp'
    pending = []
    for name, targets in TARGETS.items():
        path = base / (name + '.cs')
        text = path.read_text()
        original = text
        for target in targets:
            anchor = target + '.antiAliasing = 4;'
            call = 'PortMemorylessUI.Configure(' + target + ');'
            if text.count(anchor) != 1 or text.count(call) > 1:
                raise ValueError('Unsupported UI allocation layout: ' + name + '.' + target)
            index = text.index(anchor)
            if call in text:
                if text.index(call) != index + len(anchor) + len('\n\t\t\t'):
                    raise ValueError('Mixed UI storage patch: ' + name + '.' + target)
            else:
                text = text.replace(anchor, anchor + '\n\t\t\t' + call, 1)
        pending.append((path, original, text))
    # Validate every supported allocation before writing any source.
    for path, original, patched in pending:
        if original != patched:
            path.write_text(patched)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    apply(parser.parse_args().project)
