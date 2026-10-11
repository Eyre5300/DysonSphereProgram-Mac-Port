import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('depth_recovery',Path(__file__).parents[1]/'tools/runtime/recover_inserter_depth.py');recovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(recovery)
class DepthRecoveryLayout(unittest.TestCase):
 def source(self):return "out=root/'preflight-project/Assets/RecoveredGraphics'\n name=item['name']\n if len(sys.argv)\ncore={k for k in names if k.startswith('_ENABLE_') or k=='_DISABLE_MIP'}\nmanifest=root/'recovered-graphics-manifest.json'"
 def test_restricts_shader_and_preserves_other_features(self):
  result=recovery.adapt_recovery(self.source());self.assertIn("if name!='VF Shaders/Forward/Inserter Arrow':continue",result);self.assertIn("k.startswith('_ENABLE_') or k=='_DISABLE_MIP' or k=='SOFTPARTICLES_ON'",result);self.assertIn('inserter-depth-variants-manifest.json',result)
 def test_missing_keyword_selector_rejected(self):
  with self.assertRaises(ValueError):recovery.adapt_recovery(self.source().replace("k.startswith('_ENABLE_')","unknownSelector"))
 def test_duplicate_output_anchor_rejected(self):
  with self.assertRaises(ValueError):recovery.adapt_recovery(self.source()+"\nout=root/'preflight-project/Assets/RecoveredGraphics'")
 def test_changed_shader_selection_anchor_rejected(self):
  with self.assertRaises(ValueError):recovery.adapt_recovery(self.source().replace(" name=item['name']"," name=changed['name']"))
if __name__=='__main__':unittest.main()
