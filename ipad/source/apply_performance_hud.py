"""Expose original FPS/UPS continuously in the keyboard App only."""
import argparse
from pathlib import Path
from private_paths import private_output

OLD = 'bool flag = isRunning && (showFPS || (fps < 20f && fps > 0.01f && ups < 54f)) && UIGame.viewMode != EViewMode.Starmap;'
NEW = 'bool flag = isRunning && (DSPPadPerformanceHUD.AlwaysFPS || ((showFPS || (fps < 20f && fps > 0.01f && ups < 54f)) && UIGame.viewMode != EViewMode.Starmap));'

def adapt(text):
    if text.count(NEW) == 1 and OLD not in text:
        return text
    if text.count(OLD) != 1 or NEW in text:
        raise ValueError('Unsupported FPS visibility predicate')
    return text.replace(OLD, NEW, 1)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    path = private_output(args.project) / 'Assets/Scripts/Assembly-CSharp/UIFpsStat.cs'
    path.write_text(adapt(path.read_text()))

if __name__ == '__main__':
    main()
