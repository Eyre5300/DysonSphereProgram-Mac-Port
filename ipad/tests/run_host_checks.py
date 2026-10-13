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
    parser.add_argument('--display-only', action='store_true', help='Only resolution generation/persistence checks; no input checks')
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    source = tests.parent / 'source'
    with tempfile.TemporaryDirectory(prefix='dsp-input-checks-') as temp:
        work = Path(temp)
        for name in (() if args.display_only else ('caps_press_counter', 'keyboard_events', 'PointerTransportChecks')):
            executable = work / name
            subprocess.run([args.cxx, '-std=c++17', '-Wall', '-Wextra', str(tests / (name + '.cpp')), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
        cases = [('KeyboardQueueChecks', 'DSPPadKeyQueue'),
                 ('InputPublicationChecks', 'DSPPadKeyQueue'),
                 ('CursorBridgeHarness', 'DSPPadCursorBridge'),
                 ('DisplayPresetsHarness', 'PortDisplayPresets')]
        if args.display_only:cases=[('DisplayPresetsHarness','PortDisplayPresets')]
        for name, adapter in cases:
            executable = work / (name + '.exe')
            subprocess.run([str(args.mono), str(args.csc), '-nologo', '-define:DSP_EMU_IPAD', '-out:' + str(executable), str(tests / (name + '.cs')), str(source / (adapter + '.cs'))], check=True)
            if name == 'DisplayPresetsHarness':
                modes=[]
                # Pixel-size boundaries cover 4:3 and wider Pro/Air displays.
                # Hardware support/performance is not inferred from this harness.
                for nw,nh in [(2752,2064),(2732,2048),(2420,1668),(2388,1668),(2360,1640),(2224,1668),(2048,1536)]:
                    rate=120 if nw in (2752,2420) else 60
                    for width in (nw,1920,1600,1376,1280):
                        height=round(width*nh/nw)
                        modes.append((nw,nh,width,height,width,height,rate))
                modes += [(2752,2064,w,h,2752,2064,120) for w,h in ((0,0),(1280,720),(2266,1488),(4000,3000))]
                modes += [(1640,2360,1376,956,1376,956,60),(1668,2420,1376,948,1376,948,120)]
                for mode in modes:
                    subprocess.run([str(args.mono), str(executable), *map(str, mode)], check=True)
            else:
                subprocess.run([str(args.mono), str(executable)], check=True)
        if args.display_only:return
        executable=work/'EscapeOrderChecks.exe'
        subprocess.run([str(args.mono), str(args.csc), '-nologo', '-out:'+str(executable),
                        str(tests/'EscapeOrderChecks.cs'), str(source/'DSPPadEscapeSequence.cs'),
                        str(source/'DSPPadKeyQueue.cs')],check=True)
        subprocess.run([str(args.mono),str(executable)],check=True)
        executable=work/'EscapeContextChecks.exe'
        subprocess.run([str(args.mono), str(args.csc), '-nologo', '-out:'+str(executable),
                        str(tests/'EscapeContextChecks.cs'), str(source/'DSPPadEscapeSequence.cs'),
                        str(source/'DSPPadEscapeOrder.cs')],check=True)
        subprocess.run([str(args.mono),str(executable)],check=True)


if __name__ == '__main__':
    main()
