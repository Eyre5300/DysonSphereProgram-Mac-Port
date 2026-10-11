import importlib.util,hashlib,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cargo',Path(__file__).resolve().parents[1]/'tools/runtime/apply_cargo_import_points.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CargoImportTransform(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.project=Path(t.name);self.path=self.project/'Assets/Scripts/Assembly-CSharp/CargoPath.cs';self.path.parent.mkdir(parents=True)
  self.source='class CargoPath{\n\tpublic void Import(BinaryReader r)\n\t{\n'+m.IMPORT_OLD+'\n\t}\n'+''.join('\tpublic void '+method+'\n\t{\n\t\tTestOriginalBody();\n\t}\n' for method in m.METHODS)+'}'
  self.path.write_text(self.source);original=m.SUPPORTED_SOURCE_SHA;m.SUPPORTED_SOURCE_SHA=hashlib.sha256(self.source.encode()).hexdigest();self.addCleanup(setattr,m,'SUPPORTED_SOURCE_SHA',original)
 def test_six_insertions_only_and_idempotent(self):
  m.apply(self.project);result=self.path.read_text();self.assertEqual(result.count(m.RESTORE),5);self.assertEqual(result.replace(m.IMPORT_NEW,m.IMPORT_OLD,1).replace(m.RESTORE,''),self.source);m.apply(self.project);self.assertEqual(result,self.path.read_text())
 def test_other_version_rejected_without_write(self):
  self.path.write_text(self.source+'\n// different original');before=self.path.read_bytes()
  with self.assertRaisesRegex(ValueError,'Unsupported Windows'):m.apply(self.project)
  self.assertEqual(self.path.read_bytes(),before)
 def test_partial_patch_rejected_without_write(self):
  self.path.write_text(self.source.replace(m.IMPORT_OLD,m.IMPORT_NEW,1));before=self.path.read_bytes()
  with self.assertRaisesRegex(ValueError,'Partial'):m.apply(self.project)
  self.assertEqual(before,self.path.read_bytes())
 def test_guard_moved_to_different_method_rejected(self):
  m.apply(self.project);s=self.path.read_text();s=s.replace(m.RESTORE,'',1).replace('TestOriginalBody();','TestOriginalBody();\n'+m.RESTORE,1);self.path.write_text(s);before=self.path.read_bytes()
  with self.assertRaisesRegex(ValueError,'guard'):m.apply(self.project)
  self.assertEqual(before,self.path.read_bytes())
if __name__=='__main__':unittest.main()
