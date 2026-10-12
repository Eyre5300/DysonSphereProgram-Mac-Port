from pathlib import Path
import argparse,shutil,subprocess,json,hashlib
p=argparse.ArgumentParser(description='Compile the unchanged Mac game assembly with the matching mobile audio binding, using the Mac ARM64 AOT toolchain.')
p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--unity',type=Path,required=True);a=p.parse_args()
a.project=a.project.resolve();a.output=a.output.resolve();a.unity=a.unity.resolve()
b=a.project/'Library/Bee/artifacts';sdk=a.unity.parent/'PlaybackEngines/iOSSupport/Variations/il2cpp/Managed';tool=a.unity/'Contents/il2cpp/build/deploy/il2cpp';mac=a.unity/'Contents/PlaybackEngines/MacStandaloneSupport';i=a.output/'inputs';i.mkdir(parents=True,exist_ok=True)
original=b/'MacStandalonePlayerBuildProgram/ManagedStripped';audio=b/'iOS/ManagedStripped/UnityEngine.AudioModule.dll'
for q in i.glob('*.dll'):
 if not (original/q.name).exists():q.unlink()
for q in original.glob('*.dll'):shutil.copy2(q,i/q.name)
shutil.copy2(audio,i/audio.name)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(i/'Assembly-CSharp.dll')==sha(original/'Assembly-CSharp.dll')
a.output.mkdir(parents=True,exist_ok=True)
report={'gameAssemblyUnchanged':True,'gameSHA256':sha(i/'Assembly-CSharp.dll'),'mobileAudioSHA256':sha(audio),'nativeCompilationPlatform':'MacOSX','architecture':'ARM64','changes':['Replace only platform audio engine binding with same-version iOS stripped module; no game rule edit.'],'verifiedOnDevice':False}
(a.output/'input-receipt.json').write_text(json.dumps(report,indent=2))
args=[str(tool),'--convert-to-cpp','--compile-cpp','--platform=MacOSX','--architecture=ARM64','--configuration=Release','--directory='+str(i),'--generatedcppdir='+str(a.output/'cpp'),'--data-folder='+str(a.output/'data'),'--dotnetprofile=unityaot-macos','--emit-null-checks','--enable-array-bounds-check','--baselib-directory='+str(mac),'--outputpath='+str(a.output/'GameAssembly.dylib'),'--cachedirectory='+str(a.output/'cache'),'--profiler-report','--profiler-output-file='+str(a.output/'conversion.traceevents'),'--jobs=6']
(a.output/'command.json').write_text(json.dumps(args,indent=2))
subprocess.run(args,check=True)
report['macBinarySHA256']=sha(a.output/'GameAssembly.dylib');report['metadataSHA256']=sha(a.output/'data/Metadata/global-metadata.dat');(a.output/'input-receipt.json').write_text(json.dumps(report,indent=2));print('MAC AOT MOBILE AUDIO BINDING BUILD SUCCEEDED',flush=True)
