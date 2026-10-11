import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('memoryless_patch',Path(__file__).parents[1]/'tools/runtime/apply_memoryless_ui.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)

class MemorylessAllocationPatchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.project=Path(self.temp.name);self.source=self.project/'Assets/Scripts/Assembly-CSharp';self.source.mkdir(parents=True)
  for name,targets in patch.TARGETS.items():
   text='// Private fixture: unrelated behavior must remain.\n'+''.join(t+'.antiAliasing = 4;\n' for t in targets)+'untouched();\n'
   (self.source/(name+'.cs')).write_text(text)
  (self.source/'UIMilkyWay.cs').write_text('milkyWayRT.antiAliasing = 4;\nuntestedOnlineScene();\n')
  self.before={p.name:p.read_text() for p in self.source.glob('*.cs')}
 def test_only_four_allocations_change_and_repeat_is_idempotent(self):
  patch.apply(self.project);first={p.name:p.read_text() for p in self.source.glob('*.cs')}
  self.assertEqual(first['UIMilkyWay.cs'],self.before['UIMilkyWay.cs'])
  for name,targets in patch.TARGETS.items():
   actual=first[name+'.cs']
   for target in targets:actual=actual.replace('\n\t\t\tPortMemorylessUI.Configure('+target+');','')
   self.assertEqual(actual,self.before[name+'.cs'])
  patch.apply(self.project)
  self.assertEqual(first,{p.name:p.read_text() for p in self.source.glob('*.cs')})
 def test_unknown_layout_does_not_partially_write(self):
  p=self.source/'MechaEditorCamera.cs';p.write_text('screenRT.antiAliasing = 8;\n')
  before={p.name:p.read_text() for p in self.source.glob('*.cs')}
  with self.assertRaisesRegex(ValueError,'Unsupported'):patch.apply(self.project)
  self.assertEqual(before,{p.name:p.read_text() for p in self.source.glob('*.cs')})
 def test_duplicate_anchor_rejected(self):
  p=self.source/'UIStarmap.cs';p.write_text(p.read_text()+'starmapRT.antiAliasing = 4;\n')
  with self.assertRaisesRegex(ValueError,'Unsupported'):patch.apply(self.project)
 def test_misplaced_existing_patch_rejected(self):
  p=self.source/'DysonMapCamera.cs';p.write_text(p.read_text()+'PortMemorylessUI.Configure(screenRT);\n')
  with self.assertRaisesRegex(ValueError,'Mixed'):patch.apply(self.project)

if __name__=='__main__':unittest.main()
