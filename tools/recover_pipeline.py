#!/usr/bin/env python3
"""Recover all production shader families from local owned input in a private workspace."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path

spec=importlib.util.spec_from_file_location('recovery_checkpoint',Path(__file__).with_name('recovery_checkpoint.py'))
checkpoint=importlib.util.module_from_spec(spec);spec.loader.exec_module(checkpoint)

def run(workspace):
 workspace=workspace.resolve();statefile=workspace/'conversion-state.json';state=json.loads(statefile.read_text());r=workspace/'work/dsp-runtime';project=r/'port-project'
 if state['stage'] not in ['platform_prepared','shader_recovery_failed']:raise ValueError('Unexpected conversion stage: '+state['stage'])
 checkpoint.verify_dependencies(state)
 os.chdir(workspace);env=dict(os.environ,DSP_GAME_INPUT=state['game']);logdir=workspace/'conversion-logs';logdir.mkdir(exist_ok=True)
 def step(script,*args):
  fingerprint=hashlib.sha256((r/script).read_bytes()).hexdigest()
  if script in checkpoint.REUSABLE:
   completed=state.setdefault('completedSteps',{})
   if checkpoint.reusable(workspace,script,fingerprint,completed.get(script)):
    print('Reuse verified stage:',script,flush=True);return
   checkpoint.invalidate_following(completed,script)
   statefile.write_text(json.dumps(state,indent=2))
  print('Recover:',script,flush=True)
  with (logdir/(script+'.log')).open('w')as out:
   subprocess.run([sys.executable,str(r/script),*args],env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
  if script in checkpoint.REUSABLE:
   state.setdefault('completedSteps',{})[script]=checkpoint.capture(workspace,script,fingerprint)
   statefile.write_text(json.dumps(state,indent=2))
 def read(name):return json.loads((r/name).read_text())
 try:
  step('extract_programs.py');step('convert_programs.py');step('extract_compute_meta.py');step('recover_compute.py');step('integrate_compute.py')
  # Compute references change importer type from NativeFormatImporter to ComputeShaderImporter.
  import re
  guids={x['guid']for x in read('integrated-compute-manifest.json')}
  for p in (project/'Assets').rglob('*'):
   if p.suffix not in {'.asset','.prefab','.unity'}:continue
   text=p.read_text();updated=text
   for guid in guids:updated=updated.replace('guid: '+guid+', type: 2','guid: '+guid+', type: 3')
   if updated!=text:p.write_text(updated)
  step('extract_all_shader_meta.py');step('dump_shader_parameters.py');step('shader_parameter_parser.py');step('recover_graphics.py')
  graphics=read('recovered-graphics-manifest.json')
  allowed={'VF Shaders/Dyson Sphere/Dyson Shell Unlit','Unlit/geo-test'}
  if any(x['name']not in allowed for x in graphics['failures']):raise ValueError('Unexpected shader recovery failure')
  for row in graphics['shaders']:
   for rel in row['original_paths']:shutil.copy2(r/'preflight-project'/row['path'],project/rel)
  # Recreate the stage intermediates that the early experiments generated manually.
  ns={};exec((r/'recover_graphics.py').read_text().split('records=[];failures=[]')[0],ns)
  def stage(meta,pa,kind,stem):
   p=pa[kind];sub,pi=next((s,i)for group,ids in zip(p['m_PlayerSubPrograms'],p['m_ParameterBlobIndices'])for s,i in zip(group,ids))
   return ns['rebuild_stage'](meta,pa,kind,sub,stem+'-'+str(pi)+'.bin')[0]
  meta=read('graphics-metadata/6-globalgamemanagers.assets.json');pa=meta['m_ParsedForm']['m_SubShaders'][18]['m_Passes'][0]
  for kind in ['progGeometry','progFragment']:(r/('shell-depth-'+kind+'.hlsl')).write_text(stage(meta,pa,kind,'6-globalgamemanagers.assets'))
  meta=read('graphics-metadata/9963-resources.assets.json');pa=meta['m_ParsedForm']['m_SubShaders'][0]['m_Passes'][1];p=pa['progDomain'];sub=next(s for group in p['m_PlayerSubPrograms']for s in group);sha=meta['program_mapping'][str(sub['m_BlobIndex'])]
  subprocess.run([str(workspace/'work/SPIRV-Cross/spirv-cross'),str(workspace/'work/dsp-shader-probe/batch/programs'/(sha+'.spv')),'--version','450','--output',str(r/'painting-domain.glsl')],check=True)
  step('recover_shell_metal.py');step('recover_shell_depth_metal.py');step('recover_painting_tessellation.py')
  shutil.copy2(r/'painting-tessellation-recovered.shader',project/'Assets/Resources/dyson sphere/shaders/dyson layer painting overlay.shader')
  step('apply_metal_buffer_safety.py')
  step('recover_postfx_variants.py');step('recover_extra_feature_variants.py');step('restore_shader_metadata.py')
  selected=[]
  for row in read('graphics-metadata/index.json'):
   form=json.loads(Path(row['path']).read_text())['m_ParsedForm']
   if 'SHADOWS_SCREEN'in form['m_KeywordNames']:selected.append(row['name'])
  (r/'shadow-variant-candidates.json').write_text(json.dumps(selected))
  step('recover_lighting_variants.py','--all')
  stage_root=r/'lighting-variants-staged'
  for row in read('lighting-variants-staged/manifest.json'):
   for rel in row['paths']:shutil.copy2(stage_root/rel,project/rel)
  shutil.copytree(stage_root/'PortLightingVariants',project/'Assets/PortLightingVariants',dirs_exist_ok=True)
  # Refresh final include-only buffer bindings after all variant families exist.
  step('apply_metal_buffer_safety.py')
  step('apply_bitcast_optimizer_safety.py');step('restore_communicator_resource.py')
  step('recover_inserter_depth.py')
  step('apply_inserter_occlusion.py','--project',project)
  # Use the known integer-preserving transformation directly in recover_compute;
  # no generated kernel or manually recovered shader is shipped with these tools.
  state['stage']='shaders_recovered';state['shaderRecovery']='complete_pending_build_validation'
  state['productionShaders']=len(read('lighting-variants-staged/manifest.json'))
  state['computeShaders']=len(read('integrated-compute-manifest.json'))
  state['knownOriginalTestShader']='Unlit/geo-test retained as original export; not part of tested production rendering'
 except Exception as e:
  state['stage']='shader_recovery_failed';state['failure']=str(e);raise
 finally:statefile.write_text(json.dumps(state,indent=2))
 print('Private shader recovery complete. Unity build and gameplay validation still required.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);run(p.parse_args().workspace)
