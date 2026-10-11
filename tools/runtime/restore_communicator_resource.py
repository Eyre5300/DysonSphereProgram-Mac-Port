"""Restore the playable communicator prefab's original Resources lookup name.

AssetRipper exported the imported model and scripted prefab to the same base
name, assigning _0 to the scripted prefab. Keep both assets and their GUIDs.
"""
from pathlib import Path
import json

root = Path(__file__).resolve().parent
folder = root / 'port-project/Assets/Resources/doodads/df communicator'
canonical = folder / 'df-communicator.prefab'
scripted = folder / 'df-communicator_0.prefab'
model = folder / 'df-communicator-model.prefab'
guid = 'e5cc1da3b96bfc91d31268de58596f3f'
if guid in canonical.read_text():
    print('Communicator resource mapping already restored')
else:
    assert 'm_Script:' not in canonical.read_text()
    assert guid in scripted.read_text()
    assert not model.exists() and not Path(str(model)+'.meta').exists()
    for source, target in [(canonical, model), (scripted, canonical)]:
        source.rename(target)
        Path(str(source)+'.meta').rename(Path(str(target)+'.meta'))
    (root/'communicator-resource-fix.json').write_text(json.dumps({
        'original_resource': 'doodads/df communicator/df-communicator',
        'original_resources_assets_path_id': 46422,
        'original_model_path_id': 14425,
        'restored_component': 'CM_DFCommunicatorSimulator',
        'model_preserved_as': str(model.relative_to(root)),
        'scripted_prefab': str(canonical.relative_to(root)),
        'guid_preserved': True,
    }, indent=2)+'\n')
    print('Restored scripted communicator prefab; original model and GUIDs preserved')
