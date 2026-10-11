#!/usr/bin/env python3
"""Create a private, version-checked conversion workspace from an owned Windows game."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUPPORTED_SHA='6c122e5443e6843979b4064050dfcb5e0d75577a0b64f6ae4111290238b33c12'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def prepare(game,workspace,exported,cross,vkd3d,assetripper=None):
 game,workspace=game.resolve(),workspace.resolve()
 if workspace.exists():raise ValueError('Choose a new private workspace; existing folders are never overwritten')
 if ROOT==workspace or ROOT in workspace.parents or game==workspace or game in workspace.parents:raise ValueError('Workspace must be separate from tools and input game')
 dll=game/'DSPGAME_Data/Managed/Assembly-CSharp.dll'
 if not dll.is_file()or sha(dll)!=SUPPORTED_SHA:raise ValueError('Unsupported Windows game assembly; supported DSP version is 0.10.35.29104')
 for name in ['Locale','Updates','Configs','Icarus','Verta','Wiki']:
  if not (game/name).is_dir():raise ValueError('Missing original external data directory '+name)
 for path in [cross,vkd3d]:
  if not path.is_file()or not os.access(path,os.X_OK):raise ValueError('Missing executable dependency '+str(path))
 if exported is None and assetripper is None:raise ValueError('Provide AssetRipper 2.0 or an untouched export')
 workspace.mkdir(parents=True);r=workspace/'work/dsp-runtime';r.mkdir(parents=True)
 for p in (ROOT/'tools/runtime').glob('*.py'):shutil.copy2(p,r/p.name)
 shutil.copytree(ROOT/'runtime',workspace/'authored-runtime')
 for path,relative in [(cross,'work/SPIRV-Cross/spirv-cross'),(vkd3d,'work/vkd3d-2.1/vkd3d-compiler')]:
  dst=workspace/relative;dst.parent.mkdir(parents=True,exist_ok=True);dst.symlink_to(path.resolve())
 if exported is None:
  exported=load('export_project',ROOT/'tools/export_project.py').export(assetripper,game,r/'recovered-project')
 else:
  exported=exported.resolve();dest=r/'recovered-project/ExportedProject';dest.parent.mkdir()
  if not (exported/'Assets/Scripts/Assembly-CSharp/DSPGame.cs').is_file():raise ValueError('Not an untouched AssetRipper ExportedProject')
  shutil.copytree(exported,dest,copy_function=shutil.copyfile);exported=dest
 project=r/'port-project';shutil.copytree(exported,project,copy_function=shutil.copyfile)
 env=dict(os.environ,DSP_GAME_INPUT=str(game))
 def run(script,*args):
  print('Prepare:',script,flush=True);subprocess.run([sys.executable,str(r/script),*map(str,args)],cwd=workspace,env=env,check=True)
 run('apply_portability.py');run('apply_platform_startup.py');run('apply_runtime_fixes.py','--project',project)
 for p in (workspace/'authored-runtime').rglob('*.cs'):
  dst=project/'Assets'/p.relative_to(workspace/'authored-runtime');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
 run('apply_mac_input.py','--project',project,'--runtime',workspace/'authored-runtime')
 run('apply_minimap_buffer_lifetime.py','--project',project)
 run('apply_memoryless_ui.py','--project',project)
 run('apply_initial_upload_batch.py','--project',project)
 run('apply_cargo_import_points.py','--project',project)
 run('apply_camera_projection.py','--project',project)
 run('apply_ui_platform.py','--project',project)
 run('add_display_presets.py');run('apply_startup_display.py','--project',project);run('patch_sun_shafts.py','--project',project,'--helper',workspace/'authored-runtime/PortSunShafts.cs')
 # Locale and Verta remain local; no links into the original installation.
 stream=project/'Assets/StreamingAssets';stream.mkdir(exist_ok=True)
 for name in ['Locale','Updates','Configs','Icarus','Verta','Wiki']:
  shutil.copytree(game/name,stream/name,copy_function=shutil.copyfile)
 src=project/'Assets/Scripts/Assembly-CSharp'
 for filename,old,new in [('Localization.cs','private static readonly string DefaultLoadingPath = "Locale/";','private static readonly string DefaultLoadingPath = UnityEngine.Application.streamingAssetsPath + "/Locale/";'),('GlobalObject.cs','Application.dataPath + "/../Updates/Versions.txt"','Application.streamingAssetsPath + "/Updates/Versions.txt"')]:
  p=src/filename;s=p.read_text()
  if s.count(old)!=1:raise ValueError('Source anchor not found: '+filename)
  p.write_text(s.replace(old,new,1))
 settings={'game':str(game),'gameAssemblySha256':SUPPORTED_SHA,'project':str(project),'export':str(exported),
  'unityVersion':'2022.3.62f3c1','stage':'platform_prepared','shaderRecovery':'pending','build':'pending',
  'dependencies':{'spirvCross':{'path':str(cross.resolve()),'sha256':sha(cross)},'vkd3d':{'path':str(vkd3d.resolve()),'sha256':sha(vkd3d)}},
  'tools':{str(p.relative_to(ROOT)):sha(p)for p in ROOT.rglob('*.py')}}
 (workspace/'conversion-state.json').write_text(json.dumps(settings,indent=2))
 print('Platform stage prepared; shader recovery and build still required:',project)
 return project
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('game','workspace','spirv-cross','vkd3d'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--exported-project',type=Path);p.add_argument('--assetripper',type=Path);a=p.parse_args()
 prepare(a.game,a.workspace,a.exported_project,a.spirv_cross,a.vkd3d,a.assetripper)
