#!/usr/bin/env python3
"""Restore owned Windows circular UI sprite layout in a new private Mac build.

Asset export may replace the full sprite rectangle by its tight mesh bounds.
Retain original transparent padding, pivot and mesh metadata; never change pixels.
Only uniquely matched ring/three-action sprites with identical texture dimensions
are eligible. The output/report contain private input metadata, not release code.
"""
import argparse,collections,gc,hashlib,json,subprocess,copy
from pathlib import Path
import UnityPy

PUBLIC=Path(__file__).resolve().parents[1]
FIELDS=('m_Rect','m_Offset','m_Pivot','m_Border','m_PixelsToUnits','m_Extrude','m_IsPolygon')
RD_FIELDS=('textureRect','textureRectOffset','atlasRectOffset','settingsRaw','uvTransform','downscaleMultiplier','m_SubMeshes','m_IndexBuffer','m_VertexData','m_Bindpose')
def eligible(name):return name.startswith('ring-') or name in {'funcircle-1','funcircle-2','funcircle-3'}
def sha(data):return hashlib.sha256(data).hexdigest()
def texture(env,tree):
 from UnityPy.classes import PPtr
 ob=PPtr(**tree['m_RD']['texture'],assetsfile=env.file).read_typetree()
 return ob['m_Name'],ob['m_Width'],ob['m_Height']
def private(path):
 path=Path(path).resolve()
 if path==PUBLIC or PUBLIC in path.parents:raise ValueError('Game artifacts must stay outside public tools')
 return path

def restored_metadata(target,source):
 result=copy.deepcopy(target)
 for field in FIELDS:
  if field in source and field in result:result[field]=copy.deepcopy(source[field])
 for field in RD_FIELDS:
  if field in source['m_RD'] and field in result['m_RD']:result['m_RD'][field]=copy.deepcopy(source['m_RD'][field])
 return result

def restore_in_place(game,app,report_path):
 game=Path(game).resolve();app=private(app);report_path=private(report_path)
 dest=app/'Contents/Resources/Data';src=game/'DSPGAME_Data'
 if not dest.is_dir() or not src.is_dir():raise ValueError('Owned Windows input and Mac app required')
 original=collections.defaultdict(list)
 for p in sorted(src.glob('*.assets')):
  env=UnityPy.load(str(p))
  for ob in env.objects:
   if ob.type.name!='Sprite':continue
   s=ob.read_typetree()
   if eligible(s['m_Name']):original[(s['m_Name'],texture(env,s))].append(s)
  del env;gc.collect()
 report={'restored':[],'skipped':[],'originalPixelsUnchanged':True,'nonSelectedObjectsUnchanged':True,'sourceAssemblySha256':sha((src/'Managed/Assembly-CSharp.dll').read_bytes())}
 for p in sorted(dest.glob('*.assets')):
  env=UnityPy.load(str(p));asset=env.file;before={ob.path_id:sha(ob.get_raw_data())for ob in env.objects};selected={}
  for ob in env.objects:
   if ob.type.name!='Sprite':continue
   t=ob.read_typetree()
   if not eligible(t['m_Name']):continue
   key=(t['m_Name'],texture(env,t));matches=original.get(key,[])
   if len(matches)!=1:report['skipped'].append({'name':t['m_Name'],'reason':'missing_or_ambiguous_input'});continue
   s=matches[0];new=restored_metadata(t,s)
   if new==t:continue
   # Native texture references/atlas references remain those of this Mac app.
   ob.save_typetree(new);selected[ob.path_id]=new
   report['restored'].append({'asset':p.name,'pathID':ob.path_id,'name':t['m_Name'],'beforeRect':t['m_Rect'],'afterRect':s['m_Rect'],'beforePivot':t['m_Pivot'],'afterPivot':s['m_Pivot']})
  if selected:
   raw=asset.save();del env;gc.collect();p.write_bytes(raw);del raw
   check=UnityPy.load(str(p))
   if set(before)!=set(check.file.objects):raise ValueError('Object identity changed')
   for ob in check.objects:
    if ob.path_id not in selected:
     if sha(ob.get_raw_data())!=before[ob.path_id]:raise ValueError('Unselected object changed')
    else:
     t=ob.read_typetree();expected=selected[ob.path_id]
     for field in FIELDS:
      if field in expected and t[field]!=expected[field]:raise ValueError('Restored sprite metadata differs')
     for field in RD_FIELDS:
      if field in expected['m_RD'] and t['m_RD'][field]!=expected['m_RD'][field]:raise ValueError('Restored sprite render metadata differs')
   del check
  else:del env
  gc.collect()
 if not report['restored'] and not original:raise ValueError('No original UI sprite metadata found')
 report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False));return report

def restore(game,app,output,report):
 app=Path(app).resolve();output=private(output)
 if output.exists() or output==app:raise ValueError('Choose a new output app')
 output.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['cp','-cR',str(app),str(output)],check=True)
 result=restore_in_place(game,output,report)
 subprocess.run(['codesign','--force','--deep','--sign','-',str(output)],check=True);subprocess.run(['codesign','--verify','--deep','--strict',str(output)],check=True)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('game','app','output','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();r=restore(a.game,a.app,a.output,a.report);print('Restored circular UI sprites:',len(r['restored']))
