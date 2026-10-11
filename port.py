#!/usr/bin/env python3
"""Local-only build/validation driver. Never downloads or publishes game content."""
import argparse, hashlib, json, os, shutil, subprocess, sys, re
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent

def validate_editor(executable):
 import importlib.util
 spec=importlib.util.spec_from_file_location('editor_preflight',ROOT/'tools/editor_preflight.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.validate_editor(executable)

def doctor(args):
 game=args.game.expanduser().resolve()
 required=['DSPGAME.exe','DSPGAME_Data/Managed/Assembly-CSharp.dll','DSPGAME_Data/globalgamemanagers','DSPGAME_Data/resources.assets']
 missing=[name for name in required if not (game/name).is_file()]
 if missing:raise SystemExit('Missing owned Windows game files: '+', '.join(missing))
 dll=game/required[1]
 if dll.read_bytes()[:2]!=b'MZ':raise SystemExit('Managed assembly is not a Windows PE file')
 editor=validate_editor(args.unity)
 report={'editor':editor,'input':str(game),'managed_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'python':sys.version.split()[0],'unity':str(args.unity),'unity_available':args.unity.is_file(),'original_files_modified':False,'previously_tested_game_version':'0.10.35.29104','warning':'Input presence check only. Different game versions require conversion and runtime validation.'}
 print(json.dumps(report,ensure_ascii=False,indent=2))

def stage_tools(args):
 workspace=args.workspace.expanduser().resolve()
 if workspace==ROOT or ROOT in workspace.parents:raise SystemExit('Private workspace must be outside the publishable tools directory')
 target=workspace/'work/dsp-runtime'
 if target.exists():raise SystemExit('Workspace tooling already exists; choose a new empty workspace')
 target.mkdir(parents=True)
 manifest=[]
 for source in sorted((ROOT/'tools/runtime').glob('*.py')):
  dst=target/source.name;shutil.copy2(source,dst)
  manifest.append({'path':str(dst.relative_to(workspace)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
 helper=workspace/'authored-runtime';shutil.copytree(ROOT/'runtime',helper)
 (workspace/'tooling-manifest.json').write_text(json.dumps(manifest,indent=2))
 print('Authored tools staged:',workspace,'\nNo game files copied or converted. Follow README prerequisites.')

def build(args):
 project=args.project.expanduser().resolve();output=args.output.expanduser().resolve()
 editor=validate_editor(args.unity)
 for name in ['Assets/Scenes/level0.unity','Assets/Editor/PortBuild.cs','ProjectSettings/ProjectVersion.txt']:
  if not (project/name).is_file():raise SystemExit('Prepared local conversion project required; missing '+name)
 if ROOT==output or ROOT in output.parents:raise SystemExit('Game build output must be outside the publishable tools directory')
 if output.exists():raise SystemExit('Output already exists; choose a new path to preserve it')
 output.parent.mkdir(parents=True,exist_ok=True);log=output.parent/(output.stem+'-build.log')
 env=os.environ.copy();env['DSP_MAC_OUTPUT']=str(output);env['DSP_RELEASE_BUILD']='1' if args.release else '0'
 cmd=[str(args.unity),'-batchmode','-nographics','-noaudio','-quit','-buildTarget','OSXUniversal','-projectPath',str(project),'-executeMethod','PortBuild.BuildMac','-logFile',str(log)]
 subprocess.run(cmd,env=env,check=True)
 verify_build(output,log)
 # Circular UI layout must be read from this user's original assets, never
 # synthesized from the tight exported mesh rectangle.
 statefile=project.parents[2]/'conversion-state.json'
 if not statefile.is_file():raise SystemExit('Missing owned-input conversion-state.json for UI sprite recovery')
 state=json.loads(statefile.read_text())
 import importlib.util
 spec=importlib.util.spec_from_file_location('restore_ui_sprites',ROOT/'tools/restore_original_ui_sprites.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 sprite_report=output.parent/(output.stem+'-ui-sprites.json')
 module.restore_in_place(Path(state['game']),output,sprite_report)
 # Local ad-hoc signing covers every generated resource and native plugin.
 subprocess.run(['codesign','--force','--deep','--sign','-',str(output)],check=True)
 subprocess.run(['codesign','--verify','--deep','--strict',str(output)],check=True)
 receipt=output.parent/(output.stem+'-validation.json');data=json.loads(receipt.read_text());data['localSignatureVerified']=True;receipt.write_text(json.dumps(data,indent=2))
 print('Built locally:',output,'\nBuild log:',log)

def verify_build(output,log):
 if not (output/'Contents/Info.plist').is_file():raise SystemExit('Unity returned without a valid app; inspect '+str(log))
 content=log.read_text(errors='replace')
 errors=[line for line in content.splitlines() if re.search(r'Shader error|error CS\d+|BuildFailedException',line)]
 receipt={'app':str(output),'log':str(log),'shaderAndScriptErrors':errors,'buildLogValidated':not errors,'gameplayValidated':False}
 (output.parent/(output.stem+'-validation.json')).write_text(json.dumps(receipt,indent=2))
 if errors:raise SystemExit('Build contains shader/script errors; do not deliver this app. See '+str(log))

def prepare(args):
 import importlib.util
 spec=importlib.util.spec_from_file_location('prepare_project',ROOT/'tools/prepare_project.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.prepare(args.game,args.workspace,args.exported_project,args.spirv_cross,args.vkd3d,args.assetripper)

def recover_shaders(args):
 import importlib.util
 spec=importlib.util.spec_from_file_location('recover_pipeline',ROOT/'tools/recover_pipeline.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.run(args.workspace)

def convert(args):
 # Reuse exactly the independently tested stage implementations.
 validate_editor(args.unity)
 prepare(args)
 recover_shaders(args)
 args.project=args.workspace.expanduser().resolve()/'work/dsp-runtime/port-project'
 args.output=args.output or args.workspace.expanduser().resolve()/'build/DSPMac.app'
 build(args)
 statefile=args.workspace.expanduser().resolve()/'conversion-state.json'
 state=json.loads(statefile.read_text());state['stage']='built';state['build']='signed_and_log_checked';state['app']=str(args.output);state['gameplayValidation']='required';statefile.write_text(json.dumps(state,indent=2))

def arm_smoke(args):
 folder=Path.home()/'Library/Application Support/LocalDSPPort/DSPMacDevelopment'
 folder.mkdir(parents=True,exist_ok=True)
 (folder/'port-converter-smoke.flag').write_text('explicit local smoke test')
 print('Next launch will silently create, save and reload an isolated test world, then exit normally.')
 print('It creates a uniquely named test save; the game may update its normal last-exit autosave.')
 print('Open your generated Mac app. Result:',folder/'converter-smoke-result.json')

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 common=argparse.ArgumentParser(add_help=False);common.add_argument('--unity',type=Path,default=Path('/Applications/Unity/Unity.app/Contents/MacOS/Unity'))
 d=sub.add_parser('doctor',parents=[common]);d.add_argument('--game',type=Path,required=True);d.set_defaults(run=doctor)
 b=sub.add_parser('build',parents=[common]);b.add_argument('--project',type=Path,required=True);b.add_argument('--output',type=Path,required=True);b.add_argument('--release',action='store_true');b.set_defaults(run=build)
 t=sub.add_parser('stage-tools');t.add_argument('--workspace',type=Path,required=True);t.set_defaults(run=stage_tools)
 c=sub.add_parser('prepare');c.add_argument('--game',type=Path,required=True);c.add_argument('--workspace',type=Path,required=True);c.add_argument('--exported-project',type=Path);c.add_argument('--assetripper',type=Path);c.add_argument('--spirv-cross',type=Path,required=True);c.add_argument('--vkd3d',type=Path,required=True);c.set_defaults(run=prepare)
 c=sub.add_parser('recover-shaders');c.add_argument('--workspace',type=Path,required=True);c.set_defaults(run=recover_shaders)
 c=sub.add_parser('convert',parents=[common]);c.add_argument('--game',type=Path,required=True);c.add_argument('--workspace',type=Path,required=True);c.add_argument('--exported-project',type=Path);c.add_argument('--assetripper',type=Path);c.add_argument('--spirv-cross',type=Path,required=True);c.add_argument('--vkd3d',type=Path,required=True);c.add_argument('--output',type=Path);c.add_argument('--release',action='store_true');c.set_defaults(run=convert)
 c=sub.add_parser('arm-smoke');c.set_defaults(run=arm_smoke)
 a=p.parse_args();a.run(a)
if __name__=='__main__':main()
