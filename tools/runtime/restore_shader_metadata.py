from pathlib import Path
import json,re
root=Path('work/dsp-runtime');metadata={}
for f in (root/'graphics-metadata').glob('*.json'):
 if f.name=='index.json':continue
 p=json.loads(f.read_text())['m_ParsedForm'];metadata[p['m_Name']]=p
rows=[]
for f in (root/'port-project/Assets').rglob('*.shader'):
 s=f.read_text();m=re.search(r'Shader\s+"([^"]+)"',s)
 if not m or m[1] not in metadata:continue
 p=metadata[m[1]];changes=[]
 for prop in p['m_PropInfo']['m_Props']:
  if prop['m_Type']!=0:continue
  pattern=r'(\b'+re.escape(prop['m_Name'])+r'\s*\(\s*"[^"\n]*"\s*,\s*)Vector(\s*\))'
  s,n=re.subn(pattern,lambda x:x[1]+'Color'+x[2],s)
  if n:changes.append('Color:'+prop['m_Name'])
 fallback=p.get('m_FallbackName','')
 if fallback and re.search(r'\bFallback\s+Off',s,re.I):
  s=re.sub(r'\bFallback\s+Off',lambda _: 'Fallback '+json.dumps(fallback),s,flags=re.I);changes.append('Fallback:'+fallback)
 if changes:f.write_text(s);rows.append({'shader':m[1],'file':str(f),'changes':changes})
(root/'shader-metadata-restoration.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print('shaders',len(rows),'colors',sum(c.startswith('Color:') for r in rows for c in r['changes']),'fallbacks',sum(c.startswith('Fallback:') for r in rows for c in r['changes']))
