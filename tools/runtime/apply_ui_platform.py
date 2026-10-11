"""Keep Windows controls intact; adapt Finder and tablet details popup presentation."""
from pathlib import Path
import argparse

def apply(project):
 src=Path(project)/'Assets/Scripts/Assembly-CSharp'
 plans=[('UIBlueprintBrowser.cs','Application.OpenURL(currentDirectoryInfo.FullName);','PortFolderBrowser.OpenDirectory(currentDirectoryInfo.FullName);'),('UILoadGameWindow.cs','Application.OpenURL(GameConfig.gameSaveFolder);','PortFolderBrowser.OpenDirectory(GameConfig.gameSaveFolder);'),('UIGameMenu.cs','\t\ttechTipText = techTip.tips.tipText;','\t\tPortHUDPopupBounds.Attach(this);\n\t\ttechTipText = techTip.tips.tipText;')]
 updates={}
 for name,old,new in plans:
  p=src/name;s=p.read_text()
  if new in s:continue
  if s.count(old)!=1:raise ValueError('Unsupported UI source anchor: '+name)
  updates[p]=s.replace(old,new,1)
 for p,s in updates.items():p.write_text(s)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
