import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('wizard',Path(__file__).parents[1]/'wizard.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)

class WizardTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.base=Path(self.temp.name);self.statefile=self.base/'session.json';self.ws=self.base/'private';self.calls=[]
  self.s={'workspace':str(self.ws),'game':str(self.base/'owned'),'assetripper':'/tool/ripper','spirv_cross':'/tool/cross','vkd3d':'/tool/vkd3d','unity':'/tool/unity','textures':True,'completed':[]}
 def fake(self,cmd,**kw):
  step=cmd[2] if cmd[1].endswith('port.py') else 'textures';self.calls.append(step)
  if step=='prepare':
   (self.ws/'work/dsp-runtime/port-project').mkdir(parents=True)
   (self.ws/'conversion-state.json').write_text(json.dumps({'stage':'platform_prepared'}))
  if step=='recover-shaders':(self.ws/'conversion-state.json').write_text(json.dumps({'stage':'shaders_recovered'}))
  if '--output' in cmd:
   app=Path(cmd[cmd.index('--output')+1]);(app/'Contents').mkdir(parents=True);(app/'Contents/Info.plist').write_text('test')
 def test_success_resume_skips_all_completed(self):
  w.run_pipeline(self.s,self.statefile,self.fake);self.assertEqual(self.calls,w.STEPS)
  w.run_pipeline(self.s,self.statefile,self.fake);self.assertEqual(len(self.calls),4)
  self.assertEqual(json.loads(self.statefile.read_text())['status'],'built_needs_playtest')
 def test_shader_failure_resumes_only_failed_stage(self):
  def fail(cmd,**kw):
   if cmd[2]=='recover-shaders':raise subprocess.CalledProcessError(1,cmd)
   self.fake(cmd,**kw)
  with self.assertRaises(w.Paused):w.run_pipeline(self.s,self.statefile,fail)
  self.assertEqual(self.s['completed'],['prepare']);self.assertEqual(self.s['status'],'failed')
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertEqual(self.calls,w.STEPS)
 def test_incomplete_prepare_preserved(self):
  self.ws.mkdir();(self.ws/'sentinel').write_text('keep')
  with patch.object(w,'ask',return_value='retry'):w.run_pipeline(self.s,self.statefile,self.fake)
  backups=list(self.base.glob('private.interrupted-*'));self.assertEqual(len(backups),1)
  self.assertEqual((backups[0]/'sentinel').read_text(),'keep')
 def test_shader_checkpoint_recovered_after_process_crash(self):
  self.fake(['python','port.py','prepare']);self.fake(['python','port.py','recover-shaders']);self.calls=[]
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertEqual(self.calls,['build','textures'])
 def test_existing_build_not_overwritten_after_failure(self):
  def fail(cmd,**kw):
   self.fake(cmd,**kw)
   if cmd[2]=='build':raise subprocess.CalledProcessError(1,cmd)
  with self.assertRaises(w.Paused):w.run_pipeline(self.s,self.statefile,fail)
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertTrue((self.ws/'build/DSPMac-build-1.app').exists())
  self.assertTrue((self.ws/'build/DSPMac-build-2.app').exists())
 def test_missing_completed_artifact_rejected(self):
  self.s['completed']=['prepare']
  with self.assertRaises(ValueError):w.run_pipeline(self.s,self.statefile,self.fake)
 def test_private_output_boundaries(self):
  with self.assertRaises(ValueError):w.safe_private(w.ROOT/'output')
  with self.assertRaises(ValueError):w.safe_private(w.ROOT.parent)
  with self.assertRaises(ValueError):w.safe_private(self.base/'owned/out',self.base/'owned')
 def test_pause_no_pipeline_work(self):
  with patch('builtins.input',return_value='q'):
   with self.assertRaises(w.Paused):w.ask('test')
 def test_path_with_spaces(self):
  with patch.object(w,'ask',return_value="'/tmp/owned game'"):
   self.assertEqual(str(w.path_input('path')),'/tmp/owned game')
 def test_texture_opt_out(self):
  self.s['textures']=False;w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertEqual(self.calls,w.STEPS[:3]);self.assertEqual(self.s['app'],self.s['build_app'])

 def test_resume_preserves_result_for_same_app(self):
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.s.update(smoke_app=self.s['app'],smoke_result={'phase':'passed'},status='smoke_passed')
  self.calls=[];w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertEqual(self.calls,[]);self.assertEqual(self.s['status'],'smoke_passed')
 def test_other_app_result_does_not_validate_output(self):
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.s.update(smoke_app='/different/app',smoke_result={'phase':'passed'},smoke_armed_at=1)
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertNotIn('smoke_result',self.s);self.assertNotIn('smoke_armed_at',self.s)
  self.assertEqual(self.s['status'],'built_needs_playtest')
 def test_old_unbound_result_requires_new_test(self):
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.s['smoke_result']={'phase':'passed'}
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertNotIn('smoke_result',self.s)
 def test_document_edits_do_not_invalidate_build_checkpoint(self):
  root=self.base/'tools';root.mkdir();(root/'runtime.cs').write_text('runtime v1')
  (root/'docs.txt').write_text('text v1');(root/'requirements.txt').write_text('dependency v1')
  with patch.object(w,'ROOT',root):
   original=w.fingerprint();(root/'docs.txt').write_text('text v2')
   self.assertEqual(original,w.fingerprint())
   (root/'requirements.txt').write_text('dependency v2');self.assertNotEqual(original,w.fingerprint())

 def test_paused_smoke_keeps_original_request(self):
  w.run_pipeline(self.s,self.statefile,self.fake)
  self.s.update(smoke_app=self.s['app'],smoke_armed_at=12345)
  self.calls=[];w.run_pipeline(self.s,self.statefile,self.fake)
  self.assertEqual(self.calls,[]);self.assertEqual(self.s['smoke_armed_at'],12345)
  self.assertEqual(self.s['status'],'awaiting_smoke_result')

class NativeSmokeLogTests(unittest.TestCase):
 def log(self, app, tail='DSP_MAC_SHUTDOWN_DRAINED\nUIRunner.HandleApplicationQuit()'):
  return "Mono path[0] = '"+str(Path(app).resolve()/'Contents/Resources/Data/Managed')+"'\n"+tail
 def test_native_skipped_draw_fails_despite_clean_exit(self):
  text=self.log('/tmp/test.app')+'\nMetal: requires a ComputeBuffer. Skipping draw calls to avoid crashing.'
  state, errors=w.inspect_smoke_log(text,'/tmp/test.app');self.assertEqual(state,'failed');self.assertEqual(len(errors),1)
 def test_shader_error_fails(self):
  self.assertEqual(w.inspect_smoke_log(self.log('/tmp/test.app')+'\nShader error in example','/tmp/test.app')[0],'failed')
 def test_camera_or_managed_failure_cannot_pass_clean_exit(self):
  for message in ('Screen position out of view frustum (screen pos 0,0,150000)', 'IndexOutOfRangeException: Index was outside bounds', 'NullReferenceException: Object reference', 'Assertion failed on expression: valid'):
   with self.subTest(message=message):
    status, errors=w.inspect_smoke_log(self.log('/tmp/test.app')+'\n'+message,'/tmp/test.app')
    self.assertEqual(status,'failed');self.assertEqual(errors,[message])
 def test_other_runtime_cannot_validate_selected_app(self):
  self.assertEqual(w.inspect_smoke_log(self.log('/tmp/old.app'),'/tmp/new.app')[0],'wrong_app')
 def test_result_before_exit_remains_pending(self):
  self.assertEqual(w.inspect_smoke_log(self.log('/tmp/test.app','Game save file wrote'),'/tmp/test.app')[0],'waiting_for_exit')
 def test_clean_normal_exit_with_space_in_path_passes(self):
  self.assertEqual(w.inspect_smoke_log(self.log('/tmp/owned game/test.app'),'/tmp/owned game/test.app'),('passed',[]))

if __name__=='__main__':unittest.main()
