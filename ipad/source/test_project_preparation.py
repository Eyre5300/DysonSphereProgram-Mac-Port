import unittest
from prepare_ipad_project import input_foundation,bootstrap_defines
from apply_remaining_adapters import clipboard

class ProjectPreparation(unittest.TestCase):
    def test_shared_input_composition_preserves_sampling_order(self):
        # Synthetic sampler: models the shared installer output, not a game file.
        source='\tpublic static void OnUpdate()\n\t{\n\t\tReadAxes();\n\t\tReadModifiers();\n\t\tUpdateGameStates();\n\t\tPortMacInput.Poll();\n\t\tint frameCount = Time.frameCount;\n\t\tPublish();\n\t}\n\tpublic static void OnFixedUpdate()\n\t{\n\t\tSample();\n\t}\n'
        result=input_foundation(source)
        self.assertEqual(input_foundation(result),result)
        self.assertEqual(result.count('PortMacInput.Poll();'),1)
        self.assertEqual(result.count('DSPPadInput.Poll();'),1)
        self.assertLess(result.index('DSPPadInput.Poll();'),result.index('ReadAxes();'))
        self.assertLess(result.index('Publish();'),result.index('UpdateInputPublished();'))
        self.assertLess(result.index('Sample();'),result.index('FixedInputSampled();'))
        with self.assertRaises(ValueError):input_foundation(source.replace('PortMacInput.Poll();','UnknownPoll();'))

    def test_defines_exist_before_first_editor_compile(self):
        for block in ('  scriptingDefineSymbols: {}\n','  scriptingDefineSymbols:\n    Standalone: CUSTOM\n    Android: OTHER\n'):
            original='PlayerSettings:\n'+block+'  allowUnsafeCode: 1\n'
            result=bootstrap_defines(original)
            self.assertEqual(bootstrap_defines(result),result)
            self.assertIn('    iPhone: DSP_EMU_IPAD\n',result)
            self.assertIn('  allowUnsafeCode: 1\n',result)
            if 'CUSTOM' in original:
                self.assertIn('Standalone: CUSTOM;DSP_EMU_IPAD',result)
                self.assertIn('Android: OTHER',result)

    def test_clipboard_automatic_read_only_is_guarded(self):
        source='\t\tbpPasteButton.button.interactable = editor.blueprint.CheckValid(GUIUtility.systemCopyBuffer, EDysonBlueprintType.DysonSphere);\n\t\tExplicitPasteAndValidate();\n'
        result=clipboard(source)
        self.assertEqual(clipboard(result),result)
        self.assertIn(source.splitlines()[0],result)
        self.assertEqual(result.count('ExplicitPasteAndValidate();'),1)
        self.assertLess(result.index('#endif'),result.index('ExplicitPasteAndValidate();'))

if __name__=='__main__':unittest.main()
