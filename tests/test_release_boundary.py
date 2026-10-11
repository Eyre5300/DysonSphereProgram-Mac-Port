import importlib.util
from pathlib import Path
import tempfile,unittest
spec=importlib.util.spec_from_file_location('release_boundary',Path(__file__).resolve().parents[1]/'tools/check_release.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ReleaseBoundaryTests(unittest.TestCase):
 def test_untracked_and_ignored_game_files_are_checked(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'.git').mkdir();(r/'.gitignore').write_text('*.dll\nlocal-private/\n')
   (r/'untracked.dll').write_bytes(b'owned test sentinel');(r/'local-private').mkdir();(r/'local-private/private.txt').write_text('test sentinel')
   paths,errors=m.check_release(r)
   self.assertIn('untracked.dll',paths);self.assertIn(('untracked.dll','unexpected file type'),errors)
   self.assertIn(('local-private/private.txt','private/game path'),errors)
 def test_symlink_files_and_directories_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'source.txt').write_text('test');(r/'link.txt').symlink_to('source.txt');(r/'folder').mkdir();(r/'link-folder').symlink_to('folder',target_is_directory=True)
   _,errors=m.check_release(r)
   self.assertIn(('link.txt','symlink'),errors);self.assertIn(('link-folder','symlink'),errors)
 def test_authored_files_and_cache_only(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'tool.py').write_text('print(42)');(r/'__pycache__').mkdir();(r/'__pycache__/tool.pyc').write_bytes(b'cache');(r/'.DS_Store').write_bytes(b'metadata')
   self.assertEqual(m.check_release(r),(['tool.py'],[]))
 def test_machine_specific_path_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'config.txt').write_text('/'+'Users'+'/example/private')
   self.assertIn(('config.txt','machine-specific path'),m.check_release(r)[1])
if __name__=='__main__':unittest.main()
