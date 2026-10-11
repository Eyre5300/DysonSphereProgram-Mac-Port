import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('checkpoint', Path(__file__).resolve().parents[1]/'tools/recovery_checkpoint.py')
checkpoint = importlib.util.module_from_spec(spec); spec.loader.exec_module(checkpoint)

class RecoveryCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name); self.batch = self.ws/'work/dsp-shader-probe/batch'
        (self.batch/'programs').mkdir(parents=True)
        (self.batch/'inventory.json').write_text(json.dumps({'programs': [{'sha256': 'abc'}], 'errors': []}))
        (self.batch/'programs/abc.dxbc').write_bytes(b'owned-private-intermediate')
        self.saved = checkpoint.capture(self.ws, 'extract_programs.py', 'script-v1')
    def test_intact_checkpoint_can_resume(self):
        self.assertTrue(checkpoint.reusable(self.ws, 'extract_programs.py', 'script-v1', self.saved))
    def test_missing_intermediate_does_not_reuse(self):
        (self.batch/'programs/abc.dxbc').unlink()
        self.assertFalse(checkpoint.reusable(self.ws, 'extract_programs.py', 'script-v1', self.saved))
    def test_modified_intermediate_does_not_reuse(self):
        (self.batch/'programs/abc.dxbc').write_bytes(b'changed')
        self.assertFalse(checkpoint.reusable(self.ws, 'extract_programs.py', 'script-v1', self.saved))
    def test_old_or_changed_script_checkpoint_does_not_reuse(self):
        self.assertFalse(checkpoint.reusable(self.ws, 'extract_programs.py', 'script-v1', 'script-v1'))
        self.assertFalse(checkpoint.reusable(self.ws, 'extract_programs.py', 'script-v2', self.saved))
    def test_incomplete_program_inventory_is_rejected(self):
        (self.batch/'inventory.json').write_text(json.dumps({'programs': [{'sha256': 'abc'}], 'errors': ['failed shader']}))
        with self.assertRaises(ValueError): checkpoint.capture(self.ws, 'extract_programs.py', 'script-v1')
    def test_incomplete_conversion_is_rejected(self):
        (self.batch/'spirv-results.json').write_text(json.dumps([{'sha256': 'abc', 'returncode': 0}]))
        with self.assertRaises(ValueError): checkpoint.capture(self.ws, 'convert_programs.py', 'convert-v1')
    def test_recomputed_producer_invalidates_later_checkpoints(self):
        steps = dict.fromkeys(checkpoint.REUSABLE, 'old')
        checkpoint.invalidate_following(steps, 'extract_all_shader_meta.py')
        self.assertEqual(set(steps), set(checkpoint.REUSABLE[:3]))
    def test_external_artifact_path_is_rejected(self):
        runtime = self.ws/'work/dsp-runtime/graphics-metadata'; runtime.mkdir(parents=True)
        (runtime/'index.json').write_text(json.dumps([{'path': '/etc/hosts'}]))
        with self.assertRaises(ValueError): checkpoint.capture(self.ws, 'extract_all_shader_meta.py', 'script')

    def dependency_state(self):
        binary = self.ws/'converter'; binary.write_bytes(b'original-compiler')
        entry = {'path': str(binary), 'sha256': checkpoint.digest(binary)}
        return {'dependencies': {'spirvCross': dict(entry), 'vkd3d': dict(entry)}}
    def test_original_dependency_binary_is_accepted(self):
        checkpoint.verify_dependencies(self.dependency_state())
    def test_changed_dependency_rejected_before_recovery(self):
        state = self.dependency_state(); (self.ws/'converter').write_bytes(b'replaced-compiler')
        with self.assertRaisesRegex(ValueError, 'dependency missing or changed'):
            checkpoint.verify_dependencies(state)
    def test_missing_dependency_record_rejected(self):
        with self.assertRaises(ValueError): checkpoint.verify_dependencies({})

if __name__ == '__main__': unittest.main()
