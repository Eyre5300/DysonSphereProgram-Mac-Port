"""Read-only macOS game memory recorder. Never launches, pauses or quits a game."""
import argparse, datetime, html, json, os, plistlib, re, subprocess, time
from pathlib import Path

def size_bytes(text):
    match=re.fullmatch(r'(\d+(?:\.\d+)?)([KMGT]?)',text)
    if not match: raise ValueError(text)
    return int(float(match[1])*1024**{'':0,'K':1,'M':2,'G':3,'T':4}[match[2]])

def parse_vmmap(text):
    rows=[];active=False
    pattern=re.compile(r'^(.+?)\s+'+r'\s+'.join([r'(\d+(?:\.\d+)?[KMGT]?)']*7)+r'\s+(\d+)(?:\s+.*)?$')
    for line in text.splitlines():
        if line.startswith('REGION TYPE'):active=True;continue
        if line.startswith('MALLOC ZONE'):break
        if not active or line.startswith(('===','TOTAL')):continue
        match=pattern.match(line)
        if not match:continue
        name=match[1].strip()
        if name=='REGION TYPE':continue
        row={'type':name,'regionCount':int(match[9])}
        row.update({key:size_bytes(match[i+2]) for i,key in enumerate(['virtualBytes','residentBytes','dirtyBytes','swappedBytes','volatileBytes','nonvolatileBytes','emptyBytes'])})
        rows.append(row)
    return rows

def atomic_json(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');os.replace(temporary,path)

def find_pid(executable):
    result=subprocess.run(['ps','-axo','pid=,comm='],capture_output=True,text=True,check=True)
    ids=[int(parts[0]) for line in result.stdout.splitlines() if len(parts:=line.strip().split(None,1))==2 and parts[1]==str(executable)]
    if len(ids)>1:raise RuntimeError('Multiple matching games: select a PID explicitly')
    return ids[0] if ids else None

def render_report(out,status,samples,snapshot):
    last=samples[-1] if samples else {};values=[x['physicalFootprintBytes']/2**30 for x in samples[-720:]]
    low=min(values,default=0);high=max(values,default=1);span=max(high-low,.1)
    points=' '.join(f'{25+i*850/max(1,len(values)-1):.1f},{200-(v-low)*150/span:.1f}'for i,v in enumerate(values))
    def display(key):return f'{last[key]/2**30:.3f} GiB / {last[key]/1e9:.3f} GB' if key in last else '暂无数据'
    rows=''.join('<tr><td>'+html.escape(r['type'])+'</td>'+''.join(f'<td>{r[k]/2**30:.3f}</td>' for k in ['residentBytes','dirtyBytes','swappedBytes','virtualBytes'])+'</tr>' for r in sorted(snapshot.get('regions',[]),key=lambda x:x['dirtyBytes']+x['swappedBytes'],reverse=True)[:25])
    table='<table><tr><th>系统区域类型</th><th>驻留 GiB</th><th>脏页 GiB</th><th>换出 GiB</th><th>虚拟 GiB</th></tr>'+rows+'</table>'if rows else '<p>尚无可用区域快照。</p>'
    text=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="10"><title>戴森球内存监测</title>
<style>body{{font:16px system-ui;max-width:1000px;margin:32px auto;background:#f5f7fa;color:#172033;padding:16px}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{background:white;padding:18px;border-radius:12px}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:9px;text-align:right;border-bottom:1px solid #ddd}}td:first-child,th:first-child{{text-align:left}}small{{color:#536174}}svg{{background:white;width:100%;border-radius:12px}}a{{color:#1558b0}}</style>
<h1>戴森球内存监测</h1><p>{html.escape(status)} · PID {last.get('pid','—')} · {html.escape(last.get('localTime',''))}</p>
<div class="cards"><div class="card">物理占用<br><b>{display('physicalFootprintBytes')}</b></div><div class="card">进程生命周期峰值<br><b>{display('peakPhysicalFootprintBytes')}</b></div><div class="card">驻留 RSS<br><b>{display('residentBytes')}</b></div><div class="card">CPU<br><b>{last.get('cpuPercentOneCore',0):.1f}%</b><br><small>100%=一个核心</small></div></div>
<h2>近期物理占用</h2><svg viewBox="0 0 920 240"><text x="25" y="22">最高 {high:.3f} GiB · 最低 {low:.3f} GiB</text><polyline points="{points}" fill="none" stroke="#1558b0" stroke-width="3"/><text x="25" y="228">按时间排列；不同存档和场景的正常资源变化也会影响曲线</text></svg>
<p>物理占用来自 proc_pid_rusage 的 phys_footprint，包含计费的压缩及图形内存；RSS 不能替代它。没有采集到的帧率、具体纹理或模型内存不作估算。CPU已按Mach时钟换算。</p>
<h2>最近的详细分布快照</h2><p>{html.escape(snapshot.get('time','暂无'))} · {html.escape(snapshot.get('error',''))}</p>{table}
<p>表格是 vmmap 的系统区域统计，不能直接当作 Unity 资源分类；虚拟地址空间不等于实际占用。驻留、脏页、换出等列不可相加当作总量。未标记区域需要诊断版进一步区分托管堆和引擎分配；图形映射也不等于完整 Metal 资源总数。一次上涨不能直接判定泄漏。</p>
<p><a href="samples.ndjson">全部采样</a> · <a href="latest.json">最近采样</a> · <a href="latest-snapshot.json">分布数据</a> · <a href="latest-vmmap.txt">原始 vmmap</a></p>
<p>工具只读。不会向游戏发输入、改变画质、附加调试器、替换文件或退出游戏。窗口关闭或结束监测也不关闭游戏。页面每10秒刷新。</p></html>'''
    temporary=out/'index.html.tmp';temporary.write_text(text);os.replace(temporary,out/'index.html')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--app',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--interval',type=float,default=5);parser.add_argument('--snapshot-every',type=float,default=300);parser.add_argument('--pid',type=int);args=parser.parse_args()
    if args.interval<2 or args.snapshot_every<60:parser.error('interval>=2 seconds, snapshot-every>=60 seconds')
    app=args.app.expanduser().resolve();info=plistlib.loads((app/'Contents/Info.plist').read_bytes());executable=app/'Contents/MacOS'/info['CFBundleExecutable']
    out=args.output.expanduser().resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'samples.ndjson').exists():parser.error('Choose a new output folder to preserve prior evidence')
    helper=out/'memory-reader';source=Path(__file__).with_name('process_memory_reader.c')
    subprocess.run(['xcrun','clang','-O2','-Wall','-Wextra',str(source),'-o',str(helper)],check=True)
    atomic_json(out/'scope.json',{'app':str(app),'executable':str(executable),'readOnly':True,'intervalSeconds':args.interval,'vmmapIntervalSeconds':args.snapshot_every,'physicalSource':'proc_pid_rusage RUSAGE_INFO_V4','cpuTimeConversion':'Mach timebase to nanoseconds','noGameControl':True,'noProfilerAttachment':True,'noUnityPerResourceClaims':True})
    samples=[];previous=None;identity=None;snapshot={};next_snapshot=0
    print('Read-only recording:',out,flush=True)
    try:
        while True:
            pid=args.pid or find_pid(executable)
            if pid is None:
                render_report(out,'等待正式游戏进程；工具不会启动游戏',samples,snapshot);time.sleep(args.interval);continue
            comm=subprocess.run(['ps','-p',str(pid),'-o','comm='],capture_output=True,text=True).stdout.strip()
            if comm!=str(executable):
                if args.pid:break
                time.sleep(args.interval);continue
            result=subprocess.run([str(helper),str(pid)],capture_output=True,text=True)
            if result.returncode:
                atomic_json(out/'reader-error.json',{'time':datetime.datetime.now().astimezone().isoformat(),'pid':pid,'error':result.stderr.strip()})
                if args.pid:break
                time.sleep(args.interval);continue
            row=json.loads(result.stdout);now=time.monotonic();current=(pid,row['startAbsoluteTime'])
            if current!=identity:previous=None;identity=current;samples=[];snapshot={};next_snapshot=0
            row['cpuPercentOneCore']=0 if previous is None else max(0,100*((row['userCPUTimeNs']+row['systemCPUTimeNs'])-(previous[1]['userCPUTimeNs']+previous[1]['systemCPUTimeNs']))/1e9/(now-previous[0]))
            row['localTime']=datetime.datetime.fromtimestamp(row['timestamp']).astimezone().isoformat();previous=(now,row);samples.append(row)
            with (out/'samples.ndjson').open('a') as stream:stream.write(json.dumps(row)+'\n')
            atomic_json(out/'latest.json',row)
            if now>=next_snapshot:
                next_snapshot=now+args.snapshot_every
                try:
                    result=subprocess.run(['/usr/bin/vmmap','-summary',str(pid)],capture_output=True,text=True,timeout=25)
                    (out/'latest-vmmap.txt').write_text(result.stdout+result.stderr)
                    file=out/('vmmap-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.txt');file.write_text(result.stdout+result.stderr)
                    snapshot={'time':row['localTime'],'pid':pid,'startAbsoluteTime':row['startAbsoluteTime'],'regions':parse_vmmap(result.stdout),'rawFile':file.name,'error':result.stderr.strip() if result.returncode else ''}
                    if not snapshot['regions'] and not snapshot['error']:snapshot['error']='未解析到系统区域；查看原始快照'
                except subprocess.TimeoutExpired:snapshot={'time':row['localTime'],'pid':pid,'regions':[],'error':'vmmap 超时；保留持续总量监测'}
                atomic_json(out/'latest-snapshot.json',snapshot)
            render_report(out,'持续只读监测中',samples,snapshot)
            if len(samples)%12==1:print(json.dumps({'pid':pid,'physicalGiB':row['physicalFootprintBytes']/2**30,'peakGiB':row['peakPhysicalFootprintBytes']/2**30,'cpuPercent':row['cpuPercentOneCore'],'samples':len(samples)}),flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:pass
    finally:render_report(out,'监测已结束；没有关闭游戏',samples,snapshot)

if __name__=='__main__':main()
