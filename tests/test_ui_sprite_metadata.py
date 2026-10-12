import copy,importlib.util,unittest,sys,types,tempfile
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with patch.dict(sys.modules,{'UnityPy':types.ModuleType('UnityPy')}):
 spec=importlib.util.spec_from_file_location('ui_sprite',ROOT/'tools/restore_original_ui_sprites.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class SpriteMetadata(unittest.TestCase):
 def test_original_bounds_recovered_native_refs_pixels_retained(self):
  target={'m_Rect':{'width':46,'height':46},'m_Pivot':{'x':-.001,'y':-.001},'m_Name':'funcircle-1','m_RD':{'texture':{'m_FileID':2,'m_PathID':100},'textureRectOffset':{'x':0,'y':0},'m_VertexData':{'data':'exported'}},'atlas':{'m_PathID':999},'pixels':'owned Mac pixels'}
  source={'m_Rect':{'width':128,'height':128},'m_Pivot':{'x':.5,'y':.5},'m_RD':{'texture':{'m_FileID':0,'m_PathID':555},'textureRectOffset':{'x':64,'y':64},'m_VertexData':{'data':'owned original mesh'}}}
  unchanged=copy.deepcopy(target);result=module.restored_metadata(target,source)
  self.assertEqual(result['m_Rect'],source['m_Rect']);self.assertEqual(result['m_Pivot'],source['m_Pivot']);self.assertEqual(result['m_RD']['textureRectOffset'],source['m_RD']['textureRectOffset']);self.assertEqual(result['m_RD']['texture'],target['m_RD']['texture']);self.assertEqual(result['atlas'],target['atlas']);self.assertEqual(result['pixels'],target['pixels']);self.assertEqual(target,unchanged)
  self.assertEqual(module.restored_metadata(result,source),result)
 def test_unrelated_sprites_ineligible(self):
  for name in ['ring-256-00','funcircle-1','funcircle-2','funcircle-3']:self.assertTrue(module.eligible(name))
  for name in ['Icarus','funcircle-4','land','sphere']:self.assertFalse(module.eligible(name))
 def test_private_artifacts_rejected_under_public_symlink_or_directory(self):
  with self.assertRaises(ValueError):module.private(ROOT/'forbidden.app')
 def test_data_entry_rejects_original_or_overlapping_target(self):
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'owned/Data'
   for target in [source,source/'nested',source.parent]:
    with self.assertRaises(ValueError):module.restore_data_in_place(source,target,Path(folder)/'report.json')
 def test_existing_mac_entry_delegates_to_same_resource_operation(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder).resolve();game=root/'owned';app=root/'generated.app';report=root/'report.json'
   (game/'DSPGAME_Data').mkdir(parents=True);(app/'Contents/Resources/Data').mkdir(parents=True)
   with patch.object(module,'restore_data_in_place',return_value={'restored':[]}) as operation:
    self.assertEqual(module.restore_in_place(game,app,report),{'restored':[]})
    operation.assert_called_once_with(game/'DSPGAME_Data',app/'Contents/Resources/Data',report)
if __name__=='__main__':unittest.main()
