import copy,tempfile,unittest
from pathlib import Path
from private_paths import private_output
from batch_result import failures
class Guards(unittest.TestCase):
 def test_repository_overlap(self):
  repo=Path(__file__).resolve().parents[2]
  for path in [repo,repo/'generated',repo.parent]:
   with self.assertRaises(ValueError):private_output(path)
 def test_input_overlap(self):
  for path in ['/tmp/guard-owned','/tmp/guard-owned/child','/tmp']:
   with self.assertRaises(ValueError):private_output(path,['/tmp/guard-owned'])
 def test_symlink_overlap(self):
  with tempfile.TemporaryDirectory() as d:
   link=Path(d)/'alias';link.symlink_to(Path(__file__).resolve().parents[2],target_is_directory=True)
   with self.assertRaises(ValueError):private_output(link/'generated')
 def test_independent_output(self):
  self.assertEqual(private_output('/tmp/guard-result',['/tmp/guard-input']),Path('/tmp/guard-result').resolve())
 def state(self):
  return {'flagsVerified':True,'enteredWorld':True,'consoleExitCode':0,'batchIdentifier':'new','expectedVersion':'27','finalGameReport':{'batchIdentifier':'new','buildVersion':'27','phase':'batch_finished_normal_exit','autoTestCompleted':True,'errors':[]}}, {'completed':True,'phase':'passed','errors':[],'stages':[{'status':'passed'} for i in range(14)]}
 def test_complete(self):
  s,f=self.state();self.assertEqual(failures(s,f),[])
 def test_zero_exit_menu_or_old_report_rejected(self):
  for key,value in [('phase','main_menu'),('batchIdentifier','old'),('buildVersion','24'),('autoTestCompleted',False),('errors',['error'])]:
   s,f=self.state();s['finalGameReport'][key]=value;self.assertTrue(failures(s,f))
 def test_stale_incomplete_functional_rejected(self):
  s,f=self.state();f['stages'][-1]['status']='running';self.assertTrue(failures(s,f))
 def test_missing_functional_rejected(self):
  s,f=self.state();self.assertTrue(failures(s,None))
 def touch_state(self):
  names=['HUD included in original UI camera', 'simultaneous move and look', 'release clears movement and look', 'look tap never clicks world', 'camera zoom buttons', 'three rapid rotation buttons', 'miner original fine rotation', 'fine pointer nudge', 'cancel releases modifier', 'preview drag does not place', 'original building placement', 'belt height controls', 'belt start stage', 'belt endpoint edit does not place', 'original belt segment placement', 'sorter fixture containers', 'sorter selects source', 'sorter valid target preview', 'sorter preview does not place', 'original sorter placement', 'fullscreen blocks movement', 'save touch-built world', 'reload touch-built world']
  state,_=self.state()
  return state,{'batchIdentifier':'new','buildVersion':'27','completed':True,'phase':'passed','errors':[], 'checks':[{'name':name,'passed':True} for name in names]}
 def test_touch_evidence_identity_and_completeness(self):
  from batch_result import touch_failures
  state,report=self.touch_state();self.assertEqual(touch_failures(state,report),[])
  for key,value in [('batchIdentifier','old'),('buildVersion','28'),('completed',False),('errors',['error'])]:
   bad=copy.deepcopy(report);bad[key]=value;self.assertTrue(touch_failures(state,bad))
  for bad in [None,{},dict(report,checks=report['checks'][:-1]),dict(report,checks=report['checks']+report['checks'][:1])]:
   self.assertTrue(touch_failures(state,bad))
  bad=copy.deepcopy(report);bad['checks'][0]['passed']=False;self.assertTrue(touch_failures(state,bad))
  state['enteredWorld']=False;self.assertTrue(touch_failures(state,report))
if __name__=='__main__':unittest.main()
