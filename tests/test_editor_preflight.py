import importlib.util
import os
from pathlib import Path
import plistlib
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('editor_preflight', Path(__file__).parents[1] / 'tools/editor_preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

class EditorPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.contents = Path(self.temp.name) / 'Unity with spaces.app/Contents'
        self.executable = self.contents / 'MacOS/Unity'
        self.executable.parent.mkdir(parents=True)
        self.executable.write_text('fixture')
        self.executable.chmod(0o755)
        (self.contents / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleVersion': preflight.SUPPORTED_EDITOR}))
        (self.contents / 'PlaybackEngines/MacStandaloneSupport').mkdir(parents=True)

    def test_pinned_editor_with_space_in_path_passes(self):
        self.assertEqual(preflight.validate_editor(self.executable)['version'], preflight.SUPPORTED_EDITOR)

    def test_wrong_editor_rejected_before_launch(self):
        (self.contents / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleVersion': '6000.0.1f1'}))
        with self.assertRaisesRegex(ValueError, '版本不匹配'):
            preflight.validate_editor(self.executable)

    def test_missing_mac_component_rejected(self):
        (self.contents / 'PlaybackEngines/MacStandaloneSupport').rmdir()
        with self.assertRaisesRegex(ValueError, 'Mac 构建支持'):
            preflight.validate_editor(self.executable)

    def test_unreadable_metadata_rejected(self):
        (self.contents / 'Info.plist').write_text('not a plist')
        with self.assertRaisesRegex(ValueError, '元数据不可读'):
            preflight.validate_editor(self.executable)

    def test_nonexecutable_file_rejected(self):
        self.executable.chmod(0o644)
        with self.assertRaisesRegex(ValueError, '未找到可执行'):
            preflight.validate_editor(self.executable)

    def test_launcher_path_is_not_editor(self):
        executable = Path(self.temp.name) / 'launch-unity'
        executable.write_text('fixture'); executable.chmod(0o755)
        with self.assertRaisesRegex(ValueError, '不能用 Unity Hub'):
            preflight.validate_editor(executable)

class WizardEditorRecoveryTests(unittest.TestCase):
    def test_stored_wrong_editor_can_be_replaced_and_resumed(self):
        spec = importlib.util.spec_from_file_location('wizard_editor_recovery', Path(__file__).parents[1] / 'wizard.py')
        wizard = importlib.util.module_from_spec(spec); spec.loader.exec_module(wizard)
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def editor(name, version):
                contents = root / name / 'Contents'
                executable = contents / 'MacOS/Unity'
                executable.parent.mkdir(parents=True)
                executable.write_text('fixture'); executable.chmod(0o755)
                (contents / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleVersion': version}))
                (contents / 'PlaybackEngines/MacStandaloneSupport').mkdir(parents=True)
                return executable
            old = editor('WrongUnity.app', '6000.0.1f1')
            good = editor('SupportedUnity.app', preflight.SUPPORTED_EDITOR)
            state = dict(game=str(root/'owned'), workspace=str(root/'private'), unity=str(old),
                         assetripper=str(good), spirv_cross=str(good), vkd3d=str(good),
                         license_confirmed=True, textures=False)
            with patch.object(wizard, 'path_input', return_value=good) as select, patch.object(wizard, 'ask', return_value='done'):
                wizard.configure(state, root/'session.json')
            select.assert_called_once()
            self.assertEqual(state['unity'], str(good.resolve()))
            self.assertTrue(state['license_confirmed'])

if __name__ == '__main__':
    unittest.main()
