"""Resolve supported Unity module layouts without development-machine paths."""
from pathlib import Path

def ios_support(unity):
    app = Path(unity).expanduser().resolve()
    candidates = [app / 'Contents/PlaybackEngines/iOSSupport',
                  app.parent / 'PlaybackEngines/iOSSupport']
    for path in candidates:
        if (path / 'Trampoline/Libraries/libiPhone-lib.a').is_file():
            return path
    raise ValueError('Unity iOS Build Support is missing: install the module for this editor. Checked: ' + ', '.join(map(str, candidates)))
