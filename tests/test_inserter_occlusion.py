import importlib.util
from pathlib import Path
import tempfile,unittest
spec=importlib.util.spec_from_file_location('inserter_patch',Path(__file__).parents[1]/'tools/runtime/apply_inserter_occlusion.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
class InserterOcclusionPatchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.project=Path(self.temp.name)
  self.shader=self.project/'Assets/Resources/shaders/vff inserterarrow.shader';self.shader.parent.mkdir(parents=True)
  self.shader.write_text('Shader "'+patch.ORIGINAL+'" { ZTest Off\nZWrite Off\nBlend SrcAlpha OneMinusSrcAlpha\n// owned fragment equations fixture\n}')
  self.source=self.project/'Assets/Scripts/Assembly-CSharp/InserterRenderer.cs';self.source.parent.mkdir(parents=True)
  self.anchor='base.Init(_manager, _modelId, _objectDesc, _argBuffer, _argOffset, replaceMat);'
  self.source.write_text('void Init(GPUInstancingManager m){'+self.anchor+'}\nvoid Init(BPGPUInstancingManager m){'+self.anchor+'}')
 def test_preserves_owned_shader_and_blueprint_overload(self):
  original=self.shader.read_text();source=self.source.read_text();patch.apply(self.project)
  derived=(self.project/'Assets/Resources/PortInserterArrowOccluded.shader').read_text()
  self.assertEqual(derived.replace(patch.REPLACEMENT,patch.ORIGINAL).replace('ZTest LEqual','ZTest Off'),original)
  self.assertEqual(self.shader.read_text(),original)
  self.assertEqual(self.source.read_text().replace('\n\t\tPortInserterOcclusion.Configure(this);',''),source)
  self.assertNotIn('Configure',self.source.read_text().split('Init(BPGPUInstancingManager')[1])
  before=self.source.read_text();patch.apply(self.project);self.assertEqual(self.source.read_text(),before)
 def test_bad_shader_cannot_modify_renderer(self):
  before=self.source.read_text();self.shader.write_text('Shader "unsupported" {ZTest Off}')
  with self.assertRaisesRegex(ValueError,'Unsupported'):patch.apply(self.project)
  self.assertEqual(self.source.read_text(),before)
 def test_incorrect_overload_order_rejected(self):
  self.source.write_text(self.source.read_text().replace('GPUInstancingManager m','UnsupportedManager m',1))
  with self.assertRaisesRegex(ValueError,'ordering'):patch.apply(self.project)
 def test_derivative_conflict_rejected(self):
  (self.project/'Assets/Resources/PortInserterArrowOccluded.shader').write_text('conflicting content')
  before=self.source.read_text()
  with self.assertRaisesRegex(ValueError,'does not match'):patch.apply(self.project)
  self.assertEqual(self.source.read_text(),before)
if __name__=='__main__':unittest.main()
