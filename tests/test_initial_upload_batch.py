import importlib.util,tempfile,unittest,re
from pathlib import Path
spec=importlib.util.spec_from_file_location('batch',Path(__file__).resolve().parents[1]/'tools/runtime/apply_initial_upload_batch.py');batch=importlib.util.module_from_spec(spec);spec.loader.exec_module(batch)
class UploadBatch(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.project=Path(t.name);self.base=self.project/'Assets/Scripts/Assembly-CSharp';self.base.mkdir(parents=True)
  for name,(total,sync) in batch.COUNTS.items():
   calls='\n'.join('instBuffer.SetData(pool, i, i, 1);'for _ in range(total-sync));full='\n'.join('instBuffer.SetData(pool);'for _ in range(sync));(self.base/(name+'.cs')).write_text('class '+name+'{void Add(){'+calls+'}\npublic virtual void SyncInstBuffer(){'+full+'}}')
 def texts(self):return {p.name:p.read_text()for p in self.base.glob('*.cs')}
 def test_only_intermediate_calls_guarded_fullsync_unchanged(self):
  old=self.texts();batch.apply(self.project);new=self.texts()
  for name,source in old.items():self.assertEqual(new[name].replace(batch.GUARD,''),source);self.assertEqual(re.search(r'void SyncInstBuffer\(\)\{[^}]*\}',source).group(),re.search(r'void SyncInstBuffer\(\)\{[^}]*\}',new[name]).group())
  self.assertEqual(sum(x.count(batch.GUARD)for x in new.values()),33);batch.apply(self.project);self.assertEqual(new,self.texts())
 def test_unknown_late_file_rejected_before_writes(self):
  p=self.base/'VegeRenderer.cs';p.write_text(p.read_text().replace('instBuffer.SetData(pool);','other();',1));old=self.texts()
  with self.assertRaises(ValueError):batch.apply(self.project)
  self.assertEqual(old,self.texts())
 def test_mixed_guard_inside_file_rejected(self):
  p=self.base/'ObjectRenderer.cs';p.write_text(p.read_text().replace('instBuffer.SetData(pool, i, i, 1);',batch.GUARD+'instBuffer.SetData(pool, i, i, 1);',1));old=self.texts()
  with self.assertRaisesRegex(ValueError,'Partial'):batch.apply(self.project)
  self.assertEqual(old,self.texts())
 def test_completed_one_file_resumes_remaining_files(self):
  old=self.texts();batch.apply(self.project);done=self.texts()
  for name,source in old.items():
   if name!='ObjectRenderer.cs':(self.base/name).write_text(source)
  batch.apply(self.project);self.assertEqual(done,self.texts())
if __name__=='__main__':unittest.main()
