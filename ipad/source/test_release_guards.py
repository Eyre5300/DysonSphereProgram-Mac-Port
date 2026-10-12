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
if __name__=='__main__':unittest.main()
