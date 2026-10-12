#!/usr/bin/env python3
"""Match original screen-space shadow transport in a generated iOS copy.
Only GraphicsSettings cascade booleans and the matching Unity 2022.3 define
bit are changed. No shaders, assets, game rules or original input are bundled.
"""
import argparse,copy,json,hashlib,os,tempfile
from pathlib import Path
import UnityPy

def sha(b):return hashlib.sha256(b).hexdigest()
def apply(target,report):
 p=Path(target)
 if p.is_symlink() or 'Steam' in p.parts or 'CloudStorage' in p.parts:raise ValueError('Generated private output only')
 if p.name!='globalgamemanagers' or p.parent.name!='Data':raise ValueError('Expected generated Data/globalgamemanagers')
 raw=p.read_bytes();e=UnityPy.load(raw)
 if int(e.file.target_platform)!=9 or not str(e.file.unity_version).startswith('2022.3.'):raise ValueError('Expected iOS Unity2022.3')
 before={o.path_id:sha(o.get_raw_data()) for o in e.objects}
 o=e.file.objects[7]
 if o.type.name!='GraphicsSettings' or len(before)!=18:raise ValueError('Unexpected manager layout')
 tree=o.read_typetree();expected=copy.deepcopy(tree)
 for tier in ['Tier1','Tier2','Tier3']:expected['m_TierSettings_'+tier]['useCascadedShadowMaps']=True
 # Exact enum reflected from the installed matching Unity CoreModule:
 # BuiltinShaderDefine.UNITY_NO_SCREENSPACE_SHADOWS = 8.
 for platform in expected['m_ShaderDefinesPerShaderCompiler']:
  if platform['shaderPlatform']!=14:raise ValueError('Expected Metal defines only')
  for tier in ['Tier1','Tier2','Tier3']:platform['defines_'+tier][0]&=~(1<<8)
 if expected!=tree:o.save_typetree(expected);candidate=e.file.save()
 else:candidate=raw
 check=UnityPy.load(candidate)
 assert check.file.objects[7].read_typetree()==expected
 assert set(check.file.objects)==set(before)
 assert all(sha(check.file.objects[k].get_raw_data())==v for k,v in before.items() if k!=7)
 assert [(x.path,str(x.guid),x.type) for x in e.file.externals]==[(x.path,str(x.guid),x.type) for x in check.file.externals]
 if candidate!=raw:
  with tempfile.NamedTemporaryFile(dir=p.parent,prefix='.shadow-tier-',delete=False) as f:f.write(candidate);temp=f.name
  os.chmod(temp,p.stat().st_mode&0o777);assert p.read_bytes()==raw;os.replace(temp,p)
 result={'beforeSHA256':sha(raw),'afterSHA256':sha(candidate),'other17ObjectsByteExact':True,'onlyCascadeAndNoScreenSpaceShadowBitChanged':True,'oldDefines':tree['m_ShaderDefinesPerShaderCompiler'],'newDefines':expected['m_ShaderDefinesPerShaderCompiler'],'nativeEnumVerified':8,'runtimeVerified':False,'reference':'https://docs.unity.cn/kr/2022.3/ScriptReference/Rendering.TierSettings-cascadedShadowMaps.html'}
 Path(report).write_text(json.dumps(result,indent=2));print('Screen-space shadow tier candidate verified; device test pending')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--target',required=True);p.add_argument('--report',required=True);a=p.parse_args();apply(a.target,a.report)
