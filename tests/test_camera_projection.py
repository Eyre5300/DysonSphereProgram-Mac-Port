import importlib.util,hashlib,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('projection',Path(__file__).resolve().parents[1]/'tools/runtime/apply_camera_projection.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CameraProjectionTransform(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.project=Path(t.name);self.path=self.project/'Assets/Scripts/Assembly-CSharp/GameCamera.cs';self.path.parent.mkdir(parents=True);self.source='// authored test fixture\n'+m.ANCHOR+'\n';self.path.write_text(self.source);old=m.SUPPORTED_SOURCE_SHA;m.SUPPORTED_SOURCE_SHA=hashlib.sha256(self.source.encode()).hexdigest();self.addCleanup(setattr,m,'SUPPORTED_SOURCE_SHA',old)
 def test_original_offaxis_body_retained_idempotent(self):
  m.apply(self.project);s=self.path.read_text();self.assertEqual(s.replace(m.HOOK,''),self.source);m.apply(self.project);self.assertEqual(s,self.path.read_text())
 def test_changed_original_rejected_without_write(self):
  self.path.write_text(self.source+'// unsupported');before=self.path.read_bytes()
  with self.assertRaisesRegex(ValueError,'Unsupported'):m.apply(self.project)
  self.assertEqual(before,self.path.read_bytes())
 def test_moved_or_duplicate_guard_rejected(self):
  for s in [m.HOOK+self.source,self.source+m.HOOK,m.HOOK+m.HOOK+self.source]:
   self.path.write_text(s);before=self.path.read_bytes()
   with self.assertRaises(ValueError):m.apply(self.project)
   self.assertEqual(before,self.path.read_bytes())
if __name__=='__main__':unittest.main()
