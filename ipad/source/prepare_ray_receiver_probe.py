"""Prepare a private, opt-in iOS shader bundle to isolate receiver-beam loss.

No production shader is replaced. Generated game-derived shaders stay private.
Use a private project BEFORE apply_ray_receiver_register_fix.py is applied.
Run PortReceiverProbeBuild.Build in Unity afterwards with DSP_RAY_BUNDLE_OUTPUT.
Device use requires both --dsp-ray-receiver-audit and --dsp-ray-probes, plus
--dsp-port-test-batch. This helper is not part of normal migration.
"""
import argparse, hashlib, json, sys
from pathlib import Path
from private_paths import private_output
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/runtime'))
from typed_register_probe import transform

def prepare(project):
    source = (project/'Assets/Resources/shaders/vff unlit ray receiver gravity.shader').read_text()
    name = 'VF Shaders/Forward/Unlit Additive Ray Receiver Gravity'
    if source.count('Shader "'+name+'"') != 1:
        raise ValueError('Unexpected receiver shader')
    fade = 'r0.x = clamp((r0.xxxx * Read_cb0_0_m0(28u).xxxx).x, 0.0f, 1.0f);'
    if source.count(fade) != 3 or source.count('void frag_main()\n{') != 3:
        raise ValueError('Unexpected receiver fragment variants')
    no_depth = source.replace(fade, '// Diagnostic: bypass soft-depth fade only.\n    r0.x = 1.0f;')
    solid = source.replace('void frag_main()\n{', 'void frag_main()\n{\n    o0=float4(1,0,1,0.3);return; // Diagnostic geometry visibility only.')
    variants = {'Typed': transform(source), 'NoDepth': no_depth,
                'Solid': solid, 'TypedSolid': transform(solid), 'TypedNoDepth': transform(no_depth)}
    folder=project/'Assets/PortReceiverProbe';folder.mkdir(parents=True,exist_ok=True)
    assets=[]
    for label,text in variants.items():
        p=folder/(label+'.shader')
        p.write_text(text.replace('Shader "'+name+'"', 'Shader "Port/ReceiverProbe/'+label+'"', 1))
        assets.append(p.relative_to(project).as_posix())
    editor=project/'Assets/Editor/PortReceiverProbeBuild.cs'
    editor.write_text('''using System;using System.IO;using UnityEditor;
public static class PortReceiverProbeBuild {
 public static void Build(){
  string output=Environment.GetEnvironmentVariable("DSP_RAY_BUNDLE_OUTPUT");if(string.IsNullOrEmpty(output))throw new Exception("Private output required");Directory.CreateDirectory(output);
  var build=new AssetBundleBuild{assetBundleName="ray-probes.bundle",assetNames=new string[]{'''+','.join(json.dumps(a) for a in assets)+'''}};
  if(!BuildPipeline.BuildAssetBundles(output,new[]{build},BuildAssetBundleOptions.UncompressedAssetBundle,BuildTarget.iOS))throw new Exception("Receiver probe bundle failed");
  foreach(string path in build.assetNames)if(ShaderUtil.ShaderHasError(AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(path)))throw new Exception("Receiver probe shader error: "+path);
 }
}
''')
    return {'sourceSHA256': hashlib.sha256(source.encode()).hexdigest(), 'variants': list(variants),
            'scope': 'Diagnostic only; depth/solid variants are not production fixes.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    result=prepare(private_output(a.project));private_output(a.report).write_text(json.dumps(result,indent=2))
