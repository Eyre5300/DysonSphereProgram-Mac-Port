"""Register Mac AOT engine calls that exist in the matching iOS Unity SDK.

Generated output contains only registration declarations/calls, never recovered
game code. Unsupported platform-specific names are reported, not substituted.
"""
from pathlib import Path
import argparse, re, subprocess, json

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpp', type=Path, required=True)
    p.add_argument('--registration', type=Path, required=True)
    p.add_argument('--ios-library', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    symbols = subprocess.check_output(['nm', '-gU', str(a.ios_library)],
                                     stderr=subprocess.DEVNULL, text=True)
    available = set(re.findall(r'\b_+Z\d+(Register_[A-Za-z0-9_]+)v\b', symbols))
    calls = set()
    for f in a.cpp.glob('*.cpp'):
        calls.update(re.findall(r'il2cpp_codegen_resolve_icall\s*\("([^"]+)"\)', f.read_text()))
    text = a.registration.read_text()
    text = re.sub(r'\n\s*// DSP_MAC_AOT_EXTRA_BEGIN.*?// DSP_MAC_AOT_EXTRA_END\s*\n', '\n', text, flags=re.S)
    existing = set(re.findall(r'\b(Register_[A-Za-z0-9_]+)\(\);', text))
    added, unsupported = set(), []
    for call in sorted(calls):
        if not call.startswith(('UnityEngine.', 'UnityEngineInternal.', 'Unity.')):
            continue
        name = 'Register_' + re.sub(r'[^A-Za-z0-9_]', '_', call.split('(')[0].replace('::', '_'))
        if name in existing:
            continue
        if name in available:
            added.add(name)
        else:
            unsupported.append(call)
    at = text.rfind('}')
    if at < 0:
        raise ValueError('Unexpected engine registration file')
    extra = '\n // DSP_MAC_AOT_EXTRA_BEGIN\n'
    for name in sorted(added):
        extra += ' void ' + name + '();\n ' + name + '();\n'
    extra += ' // DSP_MAC_AOT_EXTRA_END\n'
    a.registration.write_text(text[:at] + extra + text[at:])
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps({'existingRegistrations': len(existing),
                                   'MacAOTCallNames': len(calls),
                                   'addedMatchingSDKRegistrations': sorted(added),
                                   'unmatchedPlatformCalls': unsupported,
                                   'substitutedMethods': 0}, indent=2))
    print('Matching native SDK registrations added:', len(added),
          '; unmatched platform calls:', len(unsupported))

if __name__ == '__main__':
    main()
