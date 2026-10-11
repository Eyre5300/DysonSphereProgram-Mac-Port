from pathlib import Path
import json,re,struct,subprocess,sys
root=Path('work/dsp-runtime'); programs=Path('work/dsp-shader-probe/batch/programs');cross=Path('work/SPIRV-Cross/spirv-cross').resolve();cache=root/'graphics-hlsl';cache.mkdir(exist_ok=True)
parsed=json.loads((root/'graphics-parameters/parsed.json').read_text());out=root/'preflight-project/Assets/RecoveredGraphics';out.mkdir(exist_ok=True)
shaderpaths={}
for p in (root/'recovered-project/ExportedProject/Assets').rglob('*.shader'):
 s=p.read_text();m=re.search(r'Shader\s+"([^"]+)"',s)
 if m:shaderpaths.setdefault(m[1],[]).append((p,s[:s.index('//DummyShaderTextExporter')] if '//DummyShaderTextExporter' in s else None))

def signature(sha):
 b=(programs/(sha+'.dxbc')).read_bytes();n=struct.unpack_from('<I',b,28)[0]
 for off in struct.unpack_from('<'+'I'*n,b,32):
  tag=b[off:off+4]
  if tag not in [b'ISGN',b'ISG1']:continue
  c=b[off+8:off+8+struct.unpack_from('<I',b,off+4)[0]];num=struct.unpack_from('<I',c)[0];result={};stride=24 if tag==b'ISGN' else 32
  for i in range(num):
   p=8+i*stride+(0 if tag==b'ISGN' else 4);nameoff,idx,system,typ,reg=struct.unpack_from('<IIIII',c,p);name=c[nameoff:c.index(0,nameoff)].decode()
   result[reg]=name+str(idx) if name not in ['SV_VertexID','SV_InstanceID','SV_Position'] else name
  return result
 return {}

def common_params(pa,prog):
 names={v:k for k,v in pa['m_NameIndices']};cbs=[];bindings=[];cp=prog['m_CommonParameters']
 for cb in cp['m_ConstantBuffers']:
  params=[]
  assert not cb['m_StructParams'],'common structs'
  for p in cb['m_VectorParams']:params.append(dict(name=names[p['m_NameIndex']],type=p['m_Type'],rows=1,cols=p['m_Dim'],matrix=0,array=p['m_ArraySize'],offset=p['m_Index']))
  for p in cb['m_MatrixParams']:params.append(dict(name=names[p['m_NameIndex']],type=p['m_Type'],rows=p['m_RowCount'],cols=4,matrix=1,array=p['m_ArraySize'],offset=p['m_Index']))
  cbs.append(dict(name=names[cb['m_NameIndex']],size=cb['m_Size'],params=params))
 for p in cp['m_ConstantBufferBindings']:bindings.append(dict(name=names[p['m_NameIndex']],type=1,index=p['m_Index']))
 for p in cp['m_TextureParams']:bindings.append(dict(name=names[p['m_NameIndex']],type=0,index=p['m_Index'],sampler=p['m_SamplerIndex'],dim=p['m_Dim']*2))
 for p in cp['m_BufferParams']:bindings.append(dict(name=names[p['m_NameIndex']],type=2,index=p['m_Index']))
 assert not cp['m_UAVParams'],'UAV graphics'
 return cbs,bindings

def rebuild_stage(meta,pa,stage,sub,paramblob):
 sha=meta['program_mapping'][str(sub['m_BlobIndex'])];hlsl=cache/(sha+'.hlsl')
 if not hlsl.exists():subprocess.run([str(cross),str(programs/(sha+'.spv')),'--hlsl','--shader-model','50','--hlsl-enable-compat','--output',str(hlsl)],check=True,capture_output=True)
 text=hlsl.read_text();common,bindings=common_params(pa,pa[stage]);specific=parsed[paramblob]
 cbs={x['name']:dict(x,params=list(x['params']))for x in common}
 for cb in specific['cbs']:
  if cb['name'] not in cbs:cbs[cb['name']]=cb
  else:
   target=cbs[cb['name']];seen={p['name']for p in target['params']};target['params']+= [p for p in cb['params']if p['name']not in seen]
 bindings+=specific['bindings'];cbmap={b['index']:b['name']for b in bindings if b['type']==1};declared=set();functions=[]
 pat=r'cbuffer\s+\w+\s*:\s*register\(b(\d+)\)\s*\{\s*float4\s+(\w+)\[(\d+)\]\s*:\s*packoffset\(c0\);\s*\};'
 for m in list(re.finditer(pat,text)):
  reg=int(m[1]);name=m[2];cb=cbs[cbmap[reg]];decls=[];slots={};arrcases=[]
  for p in cb['params']:
   n=p['cols'];rows=p['rows'];typ={0:'float',1:'int',2:'uint',4:'half',5:'uint'}[p['type']];pn=p['name'];array=p['array'];offset=p['offset'];assert re.fullmatch(r'[A-Za-z_]\w*',pn),pn
   ht=typ+(str(rows)+'x'+str(n) if p['matrix'] else str(n)if n>1 else '')
   if pn not in declared:decls.append(ht+' '+pn+(f'[{array}]'if array else '')+';');declared.add(pn)
   stride=n if p['matrix'] else 1
   if array:
    assert offset%16==0
    expr=(f'transpose({pn}[(index-{offset//16}u)/{stride}u])[(index-{offset//16}u)%{stride}u]'if p['matrix'] else pn+f'[index-{offset//16}u]')
    if not p['matrix'] and n<4:expr='float4('+expr+','+','.join('0.0'for _ in range(4-n))+')'
    if typ in ['int','uint']:expr='asfloat('+expr+')'
    arrcases.append(f'if(index>={offset//16}u && index<{offset//16+array*stride}u)return {expr};')
   elif p['matrix']:
    assert offset%16==0
    for col in range(n):slots[(offset//16)+col]=f'transpose({pn})[{col}]'
   else:
    for lane in range(n):
     pos=offset+lane*4;slot=slots.setdefault(pos//16,['0.0']*4);assert isinstance(slot,list)
     expr=pn+('.'+'xyzw'[lane]if n>1 else '');slot[(pos%16)//4]='asfloat('+expr+')'if typ in ['int','uint']else expr
  fun='Read_'+name;lines=decls+[f'float4 {fun}(uint index) {{']+arrcases
  for index,value in sorted(slots.items()):lines.append(f'if(index=={index}u)return '+('float4('+','.join(value)+')'if isinstance(value,list)else value)+';')
  lines+=['return 0.0.xxxx;','}'];text=text.replace(m[0],'\n'.join(lines));text=re.sub(r'\b'+re.escape(name)+r'\[([^\[\]]+)\]',lambda mm:fun+'('+mm[1]+')',text)
  assert not re.search(r'\b'+name+r'\[',text),'nested constant access'
 text=re.sub(r'\s*:\s*register\([uts]\d+\)','',text);rename={}
 for b in bindings:
  if b['type'] in [0,2]:rename['t'+str(b['index'])]=b['name']
  if b['type']==0 and b.get('sampler',-1) not in [-1,4294967295]:rename.setdefault('s'+str(b['sampler']),'sampler'+b['name'])
 if rename:text=re.sub(r'\b(?:'+'|'.join(map(re.escape,rename))+r')\b',lambda m:rename[m[0]],text)
 # Cross compiler locations mirror D3D registers; restore mesh input semantics.
 if stage=='progVertex':
  semantics=signature(sha)
  def fixinputs(m):
   body=m[0]
   for reg,sem in semantics.items():body=re.sub(r'(\bv'+str(reg)+r'\s*:\s*)TEXCOORD\d+',lambda mm:mm[1]+sem,body)
   return body
  text=re.sub(r'struct SPIRV_Cross_Input\s*\{.*?\};',fixinputs,text,flags=re.S)
 text=re.sub(r'\bmain\(',('RecoveredVert'if stage=='progVertex'else'RecoveredFrag')+'(',text)
 return text,sha

def state(pa):
 s=pa['m_State'];names=['Zero','One','DstColor','SrcColor','OneMinusDstColor','SrcAlpha','OneMinusSrcColor','DstAlpha','OneMinusDstAlpha','SrcAlphaSaturate','OneMinusSrcAlpha'];cmp=['Off','Never','Less','Equal','LEqual','Greater','NotEqual','GEqual','Always'];st=['Keep','Zero','Replace','IncrSat','DecrSat','Invert','IncrWrap','DecrWrap']
 def val(v,table=None):return '['+v['name']+']'if v['name']not in ['','<noninit>']else(table[int(v['val'])]if table else str(int(v['val'])))
 lines=[]
 if s['m_Name']:lines.append('Name '+json.dumps(s['m_Name']))
 tags=s['m_Tags']['tags'] or pa['m_Tags']['tags']
 if tags:lines.append('Tags { '+' '.join(json.dumps(k)+'='+json.dumps(v)for k,v in tags)+' }')
 for key,label,table in [('zTest','ZTest',cmp),('zWrite','ZWrite',['Off','On']),('culling','Cull',['Off','Front','Back'])]:lines.append(label+' '+val(s[key],table))
 rb=s['rtBlend0'];lines.append('Blend '+val(rb['srcBlend'],names)+' '+val(rb['destBlend'],names)+', '+val(rb['srcBlendAlpha'],names)+' '+val(rb['destBlendAlpha'],names))
 cm=rb['colMask'];lines.append('ColorMask '+('['+cm['name']+']'if cm['name']not in ['','<noninit>']else ''.join(c for n,c in [(8,'R'),(4,'G'),(2,'B'),(1,'A')]if int(cm['val'])&n)or'0'))
 if s['offsetFactor']['val'] or s['offsetUnits']['val']:lines.append('Offset '+str(s['offsetFactor']['val'])+','+str(s['offsetUnits']['val']))
 sop=s['stencilOp'];lines.append('Stencil { Ref '+val(s['stencilRef'])+' ReadMask '+val(s['stencilReadMask'])+' WriteMask '+val(s['stencilWriteMask'])+' Comp '+val(sop['comp'],cmp)+' Pass '+val(sop['pass'],st)+' Fail '+val(sop['fail'],st)+' ZFail '+val(sop['zFail'],st)+' }')
 return '\n'.join(lines)

records=[];failures=[]
for item in json.loads((root/'graphics-metadata/index.json').read_text()):
 name=item['name']
 if len(sys.argv)>1 and sys.argv[1]not in name:continue
 if name not in shaderpaths:continue
 meta=json.loads(Path(item['path']).read_text());form=meta['m_ParsedForm'];header=shaderpaths[name][0][1]
 if header is None:continue
 try:
  for prop in form['m_PropInfo']['m_Props']:
   if prop['m_Type']==0:
    header=re.sub(r'(\b'+re.escape(prop['m_Name'])+r'\s*\(\s*"[^"\n]*"\s*,\s*)Vector(\s*\))',lambda m:m[1]+'Color'+m[2],header)
  output=[header];hashes=[];skipped=[];kept=0
  for si,ss in enumerate(form['m_SubShaders']):
   if any(any(p['progGeometry']['m_PlayerSubPrograms'])for p in ss['m_Passes']):
    skipped.append(si);continue
   kept+=1
   output.append('SubShader {');tags=ss['m_Tags']['tags']
   if tags:output.append('Tags { '+' '.join(json.dumps(k)+'='+json.dumps(v)for k,v in tags)+' }')
   output.append('LOD '+str(ss['m_LOD']))
   for pa in ss['m_Passes']:
    if pa['m_Type']==1:output.append('UsePass '+json.dumps(pa['m_UseName']));continue
    if pa['m_Type']==2:output.append('GrabPass { '+(json.dumps(pa['m_TextureName'])if pa['m_TextureName']else'')+' }');continue
    assert not any(pa['progGeometry']['m_PlayerSubPrograms']),'geometry stage'
    chunks=[];feature_keywords=set()
    for stage,macro in [('progVertex','SHADER_STAGE_VERTEX'),('progFragment','SHADER_STAGE_FRAGMENT')]:
     prog=pa[stage];choices=[(s,p)for g,ps in zip(prog['m_PlayerSubPrograms'],prog['m_ParameterBlobIndices'])for s,p in zip(g,ps)]
     choices=[(s,p)for s,p in choices if not any('STEREO'in form['m_KeywordNames'][i] for i in s['m_KeywordIndices'])]
     assert choices,'no stage variants'
     # DSP uses custom instancing and animation keywords for its indirect
     # world draws. A base-only shader places all instances at the origin.
     core={k for k in form['m_KeywordNames'] if k.startswith('_ENABLE_') or k=='_DISABLE_MIP'}
     groups={}
     for sub,pi in choices:
      flags=frozenset(form['m_KeywordNames'][i] for i in sub['m_KeywordIndices']) & core
      groups.setdefault(flags,[]).append((sub,pi))
     relevant=set().union(*groups)
     feature_keywords.update(relevant)
     variants=[]
     for flags,group in sorted(groups.items(),key=lambda pair:(-len(pair[0]),sorted(pair[0]))):
      sub,pi=min(group,key=lambda sp:(len(sp[0]['m_KeywordIndices']),sp[0]['m_KeywordIndices']))
      paramblob=Path(item['path']).stem+'-'+str(pi)+'.bin'
      code,sha=rebuild_stage(meta,pa,stage,sub,paramblob);hashes.append(sha)
      condition=' && '.join(('' if k in flags else '!')+'defined('+k+')' for k in sorted(relevant)) or '1'
      variants.append((condition,code))
     body=[]
     for vi,(condition,code) in enumerate(variants):body+=['#if '+condition if vi==0 else '#elif '+condition,code]
     body+=['#else',variants[-1][1],'#endif']
     chunks.append('#if defined('+macro+')\n'+'\n'.join(body)+'\n#endif')
    pragmas=['#pragma multi_compile __ '+k for k in sorted(feature_keywords)]
    output+=['Pass {',state(pa),'HLSLPROGRAM','#pragma target 5.0','#pragma vertex RecoveredVert','#pragma fragment RecoveredFrag',*pragmas,*chunks,'ENDHLSL','}']
   output.append('}')
  assert kept>0,'all subshaders require geometry stage'
  output.append(('Fallback '+json.dumps(form['m_FallbackName']) if form.get('m_FallbackName') else 'Fallback Off')+'\n}');target=out/(Path(item['path']).stem+'.shader');target.write_text('\n'.join(output))
  records.append(dict(name=name,path=str(target.relative_to(root/'preflight-project')),original_paths=[str(p.relative_to(root/'recovered-project/ExportedProject'))for p,_ in shaderpaths[name]],programs=hashes,skipped_geometry_subshaders=skipped))
  print('OK',name,flush=True)
 except Exception as ex:
  failures.append(dict(name=name,error=str(ex)));print('FAIL',name,str(ex),flush=True)
(root/'recovered-graphics-manifest.json').write_text(json.dumps(dict(shaders=records,failures=failures),indent=2));print('COMPLETE',len(records),'recovered',len(failures),'failed')
