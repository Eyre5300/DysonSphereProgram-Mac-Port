"""Run authored input/display transport checks without a game export or device.

Pass the licensed Unity installation's Mono and Roslyn csc.exe paths explicitly.
Generated executables live only in an automatically removed temporary directory.
These checks do not establish physical keyboard/mouse or gameplay equivalence.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mono', type=Path, required=True)
    parser.add_argument('--csc', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    source = tests.parent / 'source'
    with tempfile.TemporaryDirectory(prefix='dsp-input-checks-') as temp:
        work = Path(temp)
        for name in ('caps_press_counter', 'keyboard_events', 'PointerTransportChecks'):
            executable = work / name
            subprocess.run([args.cxx, '-std=c++17', '-Wall', '-Wextra', str(tests / (name + '.cpp')), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
        cases = [('KeyboardQueueChecks', 'DSPPadKeyQueue'),
                 ('InputPublicationChecks', 'DSPPadKeyQueue'),
                 ('CursorBridgeHarness', 'DSPPadCursorBridge'),
                 ('DisplayPresetsHarness', 'PortDisplayPresets')]
        for name, adapter in cases:
            executable = work / (name + '.exe')
            subprocess.run([str(args.mono), str(args.csc), '-nologo', '-define:DSP_EMU_IPAD', '-out:' + str(executable), str(tests / (name + '.cs')), str(source / (adapter + '.cs'))], check=True)
            if name == 'DisplayPresetsHarness':
                modes = [(2752, 2064, w, w * 3 // 4, w, w * 3 // 4) for w in (2752, 1920, 1600, 1376, 1280)]
                modes += [(2752, 2064, w, h, 2752, 2064) for w, h in ((0, 0), (1280, 720), (2266, 1488), (4000, 3000))]
                modes += [(2420, 1668, 1376, 948, 1376, 948), (2360, 1640, 1600, 1112, 1600, 1112)]
                for mode in modes:
                    subprocess.run([str(args.mono), str(executable), *map(str, mode)], check=True)
            else:
                subprocess.run([str(args.mono), str(executable)], check=True)


if __name__ == '__main__':
    main()
