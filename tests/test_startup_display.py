import importlib.util,tempfile,unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('startup_display',Path(__file__).resolve().parents[1]/'tools/runtime/apply_startup_display.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class StartupDisplayTransform(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.project=Path(tmp.name);self.path=self.project/'Assets/Scripts/Assembly-CSharp/DSPGame.cs';self.path.parent.mkdir(parents=True)
  self.original='// authored fixture: loaded configuration precedes Start\nvoid Awake(){globalOption.LoadGlobal();}\n'+m.ANCHOR+'\n}\nvoid UserApply(){globalOption.Apply();}\n'
  self.path.write_text(self.original)
 def test_only_startup_apply_hook_and_reversible(self):
  m.apply(self.project);patched=self.path.read_text();self.assertEqual(patched.replace(m.HOOK,''),self.original);self.assertIn('void UserApply(){globalOption.Apply();}',patched)
 def test_idempotent(self):
  m.apply(self.project);once=self.path.read_bytes();m.apply(self.project);self.assertEqual(once,self.path.read_bytes())
 def test_unknown_order_and_duplicate_rejected_without_write(self):
  for text in [self.original.replace('NewVersionOverrideOptions();','DifferentStartup();'),self.original+self.original]:
   self.path.write_text(text);before=self.path.read_bytes()
   with self.assertRaises(ValueError):m.apply(self.project)
   self.assertEqual(before,self.path.read_bytes())
 def test_partial_or_moved_hook_rejected_without_write(self):
  for text in [m.HOOK+self.original,self.original+m.HOOK,m.PATCHED+'\n'+m.HOOK]:
   self.path.write_text(text);before=self.path.read_bytes()
   with self.assertRaises(ValueError):m.apply(self.project)
   self.assertEqual(before,self.path.read_bytes())

if __name__=='__main__':unittest.main()
