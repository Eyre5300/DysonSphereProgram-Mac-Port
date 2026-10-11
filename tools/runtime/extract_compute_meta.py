"""Extract compute metadata from a private AssetRipper YAML export, keeping hex strings."""
from pathlib import Path
import json,re,yaml
# Disable implicit numeric resolution for fields that are serialized raw bytes.
class Loader(yaml.SafeLoader):pass
Loader.yaml_implicit_resolvers={k:list(v) for k,v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
def mapping(loader,node,deep=False):
 d={}
 for k,v in node.value:
  key=loader.construct_object(k,deep=deep)
  d[key]=v.value if key in {'code','cbVariantIndices','threadGroupSize'} else loader.construct_object(v,deep=deep)
 return d
Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
r=Path('work/dsp-runtime');rows=[]
for p in (r/'recovered-project/ExportedProject/Assets').rglob('*.asset'):
 s=p.read_text()
 if not re.search(r'^ComputeShader:',s,re.M):continue
 s=re.sub(r'^%[^\n]*\n','',s,flags=re.M);s=re.sub(r'^--- !u!\d+ &\d+','---',s,flags=re.M)
 s=re.sub(r'(?m)^(\s*)- :',r'\1- "":',s)
 data=yaml.load(s,Loader=Loader)['ComputeShader'];rows.append({'path':str(p),'data':data})
if len(rows)!=19:raise ValueError('Expected 19 compute shaders for supported game version; got '+str(len(rows)))
(r/'compute-metadata.json').write_text(json.dumps(rows));print('Extracted',len(rows),'compute assets')
