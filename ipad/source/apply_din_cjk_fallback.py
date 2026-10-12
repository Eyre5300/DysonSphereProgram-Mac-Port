#!/usr/bin/env python3
"""Append an existing game CJK fallback to DIN in a private iPad Data candidate.
Original DIN glyphs, symbols, font bytes, metrics and UI rectangles are untouched.
This intentionally replaces unavailable OS fallback for previously absent CJK;
its typeface need not be pixel-identical to Windows/macOS system font defaults.
"""
import argparse,copy,hashlib,json,os
from pathlib import Path
import UnityPy

PINNED = {1551: ('DIN','3fe23bed841463c41f9fa854215540c85f5cefc1db6019e4b95f30ca941af88a'),
          1549: ('STXIHEI','f4ccbf1caf92f38ee8f8d63edf7cf78856fdf964982d719632ef3f6960ab9fea'),
          1547: ('YC-DSP-PSYM','0aeeb78503fa5aa67de4d9161d2c464fd3005078b89ff15c4495f86aab62e2f1')}
def sha(b):return hashlib.sha256(b).hexdigest()
def check(c,m):
 if not c:raise ValueError(m)
def refs(a):return [(r.path,r.guid,r.type,r.temp_empty) for r in a.externals],[(r.local_serialized_file_index,r.local_identifier_in_file) for r in a.script_types]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset',required=True,type=Path);p.add_argument('--report',required=True,type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
 file=a.asset.resolve();check(file.name=='sharedassets0.assets','Expected audited scene assets');check(UnityPy.__version__=='1.25.4','Requires audited UnityPy1.25.4')
 if a.apply:check('local-private' in file.parts and any(x.startswith(('full-game-bc-data-','full-game-font-data-')) for x in file.parts),'Apply only to a fresh private package Data candidate')
 env=UnityPy.load(str(file));asset=env.file;before={o.path_id:sha(o.get_raw_data()) for o in env.objects};references=refs(asset);originalSHA=sha(file.read_bytes())
 for pid,(name,digest) in PINNED.items():
  o=asset.objects[pid];d=o.read_typetree();check(o.type.name=='Font' and d['m_Name']==name and sha(bytes(d['m_FontData']))==digest,'Original font identity/bytes mismatch')
 old=asset.objects[1551].read_typetree();check(old['m_FontNames']==['1234567890','YC-DSP-PSYM'] and old['m_FallbackFonts']==[{'m_FileID':0,'m_PathID':1547}],'Unrecognized or already adapted DIN fallback chain')
 new=copy.deepcopy(old);new['m_FontNames'].append('STXihei');new['m_FallbackFonts'].append({'m_FileID':0,'m_PathID':1549})
 report={'status':'plan-verified','originalAssetSHA256':originalSHA,'fontDataSHA256':{v[0]:v[1] for v in PINNED.values()},'font':'DIN','beforeFontNames':old['m_FontNames'],'afterFontNames':new['m_FontNames'],'beforeReferences':old['m_FallbackFonts'],'afterReferences':new['m_FallbackFonts'],'changedFields':['m_FontNames','m_FallbackFonts'],'fontDataUnchanged':True,'runtimeVerified':False,'parityLimit':'CJK glyphs use the existing game STXihei face instead of unavailable OS fallback; Windows/Mac OS typeface pixel identity is not claimed.'}
 if a.apply:
  asset.objects[1551].save_typetree(new);data=asset.save();tmp=file.with_suffix('.font-adapt.tmp');check(not tmp.exists(),'Temporary output exists');tmp.write_bytes(data)
  verify=UnityPy.load(str(tmp));check(set(verify.file.objects)==set(before),'Object IDs changed');check(refs(verify.file)==references,'External/script references changed')
  for o in verify.objects:
   if o.path_id==1551:check(o.read_typetree()==new,'DIN changed outside exact fallback fields')
   else:check(sha(o.get_raw_data())==before[o.path_id],'Other object changed: '+str(o.path_id))
  check(sha(file.read_bytes())==originalSHA,'Input changed during validation');os.replace(tmp,file)
  report.update(status='applied-object-byte-verified',unchangedOtherObjects=len(before)-1,outputAssetSHA256=sha(file.read_bytes()))
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
