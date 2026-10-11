import importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ui_platform',ROOT/'tools/runtime/apply_ui_platform.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class UIPlatform(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.project=Path(t.name);self.src=self.project/'Assets/Scripts/Assembly-CSharp';self.src.mkdir(parents=True)
  for name,source in {'UIBlueprintBrowser.cs':'if(active) { Application.OpenURL(currentDirectoryInfo.FullName); }','UILoadGameWindow.cs':'if(showButton.interactable) { Application.OpenURL(GameConfig.gameSaveFolder); }','UIGameMenu.cs':'\t\ttechTipText = techTip.tips.tipText;\n detailFuncGroup.gameObject.SetActive(false);'}.items():(self.src/name).write_text(source)
 def texts(self):return {p.name:p.read_text()for p in self.src.glob('*.cs')}
 def test_only_platform_calls_change_and_reapply_is_stable(self):
  before=self.texts();module.apply(self.project);after=self.texts();module.apply(self.project);self.assertEqual(after,self.texts())
  for name,s in after.items():
   restored=s.replace('PortFolderBrowser.OpenDirectory','Application.OpenURL').replace('\t\tPortHUDPopupBounds.Attach(this);\n','')
   self.assertEqual(restored,before[name])
 def test_unknown_last_anchor_fails_before_any_mutation(self):
  (self.src/'UIGameMenu.cs').write_text('unknown source');before=self.texts()
  with self.assertRaises(ValueError):module.apply(self.project)
  self.assertEqual(before,self.texts())
if __name__=='__main__':unittest.main()
