"""Create opt-in terrain compiler probes in a private project; never replace production shaders."""
import argparse, hashlib, json, re, sys
from pathlib import Path
from private_paths import private_output
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/runtime'))
from typed_register_probe import transform

def prepare(project):
    assets=project/'Assets'
    original=assets/'Resources/shaders/vff planetsurface.shader'
    source=original.read_text()
    if source.count('Shader "VF Shaders/Forward/Planet Surface"')!=1 or '#pragma skip_optimizations metal' not in source:
        raise ValueError('Unsupported recovered terrain shader')
    folder=assets/'Resources/PortSceneAudit';folder.mkdir(parents=True,exist_ok=True)
    result=source.replace('Shader "VF Shaders/Forward/Planet Surface"','Shader "Port/SceneAudit/TerrainTyped"',1).replace('#pragma skip_optimizations metal\n','')
    includes=sorted(set(re.findall(r'#include "(Assets/PortLightingVariants/[^\"]+)"',source)))
    if not includes:raise ValueError('Terrain variant includes missing')
    hashes={}
    for name in includes:
        p=project/name;text=p.read_text();target=folder/p.name
        target.write_text(transform(text));hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        result=result.replace(name,target.relative_to(project).as_posix())
    (folder/'TerrainTyped.shader').write_text(result)
    postfx=[]
    for index,filename in enumerate(('ambientocclusion.shader','bloom.shader','depthoffield.shader','fxaa.shader','uber.shader')):
        shader=assets/'Resources/shaders'/filename
        text=shader.read_text();name=re.search(r'Shader "([^"]+)"',text)[1]
        if not name.startswith('Hidden/Post FX/') or '#pragma skip_optimizations metal' not in text:
            raise ValueError('Unsupported post-processing probe: '+filename)
        resource='PostFx'+str(index);target_text=text.replace('Shader "'+name+'"','Shader "Port/SceneAudit/'+resource+'"',1).replace('#pragma skip_optimizations metal\n','')
        paths=sorted(set(re.findall(r'#include "(Assets/PortRecoveredVariants/[^"]+)"',text)))
        if not paths:raise ValueError('Post-processing variant includes missing')
        for include in paths:
            include_path=project/include;target=folder/('fx-'+include_path.name)
            target.write_text(transform(include_path.read_text()))
            target_text=target_text.replace(include,target.relative_to(project).as_posix())
        (folder/(resource+'.shader')).write_text(target_text)
        postfx.append({'original':name,'resource':'PortSceneAudit/'+resource,'sourceSHA256':hashlib.sha256(shader.read_bytes()).hexdigest()})
    (folder/'PostFxManifest.json').write_text(json.dumps({'items':postfx},indent=2))
    return {'scope':'Opt-in diagnostic only; original shaders unchanged','sourceSHA256':hashlib.sha256(original.read_bytes()).hexdigest(),'includes':hashes,'postfx':postfx}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    result=prepare(private_output(a.project));report=private_output(a.report);report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2))
