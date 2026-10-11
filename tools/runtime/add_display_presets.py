from pathlib import Path
root=Path(__file__).resolve().parent/'port-project/Assets'
p=root/'Scripts/Assembly-CSharp/GameResolutions.cs';s=p.read_text()
if 'public string displayName;' not in s:
 s=s.replace('public int width;', 'public string displayName;\n\n\t\tpublic int width;',1)
 anchor='\t\t\twindowedResolutions.Add(mergedResolutions[j]);\n\t\t}'
 if s.count(anchor)!=1:raise ValueError('Unsupported original resolution enumeration')
 s=s.replace(anchor,anchor+"\n#if UNITY_STANDALONE_OSX || UNITY_IOS || UNITY_EDITOR_OSX\n        PortDisplayPresets.Add(windowedResolutions, true);\n        PortDisplayPresets.Add(mergedResolutions, false);\n        PortDisplayPresets.Add(rawResolutions, false);\n#endif",1)
 s=s.replace('item.width = item.height;', 'int portraitWidth = item.width; item.width = item.height; item.height = portraitWidth;')
 p.write_text(s)
p=root/'Scripts/Assembly-CSharp/UIOptionWindow.cs';s=p.read_text();s=s.replace('items.Add(text + " x " + text2 + (string)obj);','items.Add(string.IsNullOrEmpty(item.displayName) ? text + " x " + text2 + (string)obj : item.displayName + "  " + text + "×" + text2);')
s=s.replace('Screen.SetResolution(tempOption.resolution.width, tempOption.resolution.height, fullscreenMode, tempOption.resolution.refreshRateRatio);','PortDisplayPresets.Apply(tempOption.resolution, fullscreenMode);');p.write_text(s)
p=root/'Scripts/Assembly-CSharp/GameOption.cs';s=p.read_text();s=s.replace('Screen.SetResolution(resolution.width, resolution.height, fullscreenMode, resolution.refreshRateRatio);','PortDisplayPresets.Apply(resolution, fullscreenMode);');p.write_text(s)
