import os
from pathlib import Path
import json,subprocess,re,shutil
r=Path('work/dsp-runtime');proj=r/'port-project';assets=proj/'Assets';src=assets/'Scripts/Assembly-CSharp'
manifest=json.loads((r/'integrated-compute-manifest.json').read_text());guids=[e['guid'] for e in manifest]
files=subprocess.check_output(['rg','-l','|'.join(guids),str(assets),'--glob','*.asset','--glob','*.prefab','--glob','*.unity'],text=True).splitlines()
for file in files:
 p=Path(file);s=p.read_text();old=s
 for guid in guids:s=s.replace('guid: '+guid+', type: 2','guid: '+guid+', type: 3')
 if s!=old:p.write_text(s);print('Fixed reference type',p)
depot=Path(os.environ['DSP_GAME_INPUT'])
stream=assets/'StreamingAssets';stream.mkdir(exist_ok=True)
for name in ['Locale','Updates','Configs','Icarus','Verta','Wiki']:
 shutil.copytree(depot/name,stream/name,dirs_exist_ok=True)
p=src/'Localization.cs';s=p.read_text();s=s.replace('private static readonly string DefaultLoadingPath = "Locale/";','private static readonly string DefaultLoadingPath = UnityEngine.Application.streamingAssetsPath + "/Locale/";');p.write_text(s)
p=src/'GlobalObject.cs';s=p.read_text().replace('Application.dataPath + "/../Updates/Versions.txt"','Application.streamingAssetsPath + "/Updates/Versions.txt"');p.write_text(s)
print('Bundled external game data')
