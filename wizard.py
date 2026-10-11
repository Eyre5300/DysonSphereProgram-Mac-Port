#!/usr/bin/env python3
"""Interactive, checkpointed local conversion. No accounts or secrets are collected."""
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SUPPORTED_SHA = '6c122e5443e6843979b4064050dfcb5e0d75577a0b64f6ae4111290238b33c12'
DEFAULT_SESSION = Path.home() / 'Library/Application Support/DSPPortConverter/session.json'
STEPS = ['prepare', 'recover-shaders', 'build', 'textures']

class Paused(Exception):
    pass

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(temp, path)

def fingerprint():
    h = hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and (p.suffix in {'.py', '.cs', '.c', '.h'} or p.name == 'requirements.txt') and 'tests' not in p.relative_to(ROOT).parts:
            h.update(str(p.relative_to(ROOT)).encode()); h.update(p.read_bytes())
    return h.hexdigest()

def ask(message, default=None):
    suffix = f' [{default}]' if default else ''
    try:
        answer = input(message + suffix + '\n> ').strip()
    except (EOFError, KeyboardInterrupt):
        raise Paused()
    if answer.lower() in {'q', 'quit', '退出'}:
        raise Paused()
    return answer or (str(default) if default is not None else '')

def path_input(message, default=None):
    while True:
        text = ask(message, default)
        # Accept a quoted path or one dragged from Finder into Terminal.
        try:
            parts = shlex.split(text)
            raw = parts[0] if len(parts) == 1 else text
        except ValueError:
            raw = text
        if raw:
            return Path(raw).expanduser().absolute()

def safe_private(path, game=None):
    path = path.resolve()
    if path == ROOT or ROOT in path.parents or path in ROOT.parents:
        raise ValueError('私有输出必须与 port-tools 分开，不能放在公开工具目录内或覆盖它。')
    if game:
        game = Path(game).resolve()
        if path == game or game in path.parents or path in game.parents:
            raise ValueError('输出与原始 Windows 游戏目录必须互不包含。')

def instructions():
    print('''戴森球计划 → Mac 本地转换向导（开发版）
只读取你购买的 Windows 游戏；不会上传文件，也不会收集密码。
目前仅验证 DSP 0.10.35.29104 / Apple Silicon Mac。iPad 部署不在本向导内。
需要你操作时会说明步骤；完成后回车重新检查。输入 q 可暂停，重新运行继续。
已完成的阶段会保留；失败阶段保留日志和产物，不会删除你的文件。
第三方依赖需要自行安装；本程序不会代替你同意许可。
''')

def configure(s, statefile):
    if not s.get('game'):
        print('在 Steam 的 Windows 安装中找到 DSPGAME.exe 所在文件夹；也可使用你购买账号下载的 Windows depot。')
        while True:
            game = path_input('拖入或输入 Windows 游戏文件夹')
            dll = game / 'DSPGAME_Data/Managed/Assembly-CSharp.dll'
            missing = [n for n in ['DSPGAME.exe', 'DSPGAME_Data/resources.assets', 'DSPGAME_Data/globalgamemanagers', 'Locale', 'Updates', 'Configs', 'Icarus', 'Verta', 'Wiki'] if not (game/n).exists()]
            if missing or not dll.is_file():
                print('文件不完整：', ', '.join(missing), '；需要完整 Windows 游戏文件。'); continue
            if hashlib.sha256(dll.read_bytes()).hexdigest() != SUPPORTED_SHA:
                print('此游戏版本尚未支持。请提供已验证的 0.10.35.29104；不会跳过校验。'); continue
            s['game'] = str(game.resolve()); save(statefile, s); break
    if not s.get('workspace'):
        while True:
            ws = path_input('选择一个尚不存在的本地工作文件夹（避免 iCloud/OneDrive；建议至少 50 GiB 可用空间）', Path.home()/'DSPPortWork')
            try:
                safe_private(ws, s['game'])
                if ws.exists(): raise ValueError('该目录已存在，请选择新名称；不会覆盖。')
            except ValueError as e:
                print(e); continue
            s['workspace'] = str(ws); save(statefile, s); break
    deps = [
        ('unity', 'Unity 2022.3.62f3c1：通过 Unity Hub 安装编辑器及 Mac 构建支持，登录并自行激活适用许可。若窗口要求同意条款，请阅读后自行决定。\n来源：https://unity.com/releases/editor/archive\n输入 Unity.app/Contents/MacOS/Unity 的路径', '/Applications/Unity/Unity.app/Contents/MacOS/Unity'),
        ('assetripper', 'AssetRipper 2.0.0：从 https://github.com/AssetRipper/AssetRipper 获取适用的 Mac 版本，按上游说明安装。输入 AssetRipper.GUI.Free 可执行文件路径', None),
        ('spirv_cross', 'SPIRV-Cross：按 docs/dependencies.txt 中固定提交及上游 CMake 说明构建，输入 spirv-cross 可执行文件路径', None),
        ('vkd3d', 'vkd3d 2.1：按 docs/dependencies.txt 构建，输入 vkd3d-compiler 可执行文件路径', None),
    ]
    for key, message, default in deps:
        while not s.get(key) or not Path(s[key]).is_file() or not os.access(s[key], os.X_OK):
            p = path_input(message, s.get(key, default))
            if not p.is_file() or not os.access(p, os.X_OK):
                print('尚未检测到可执行文件。完成安装后重试，或 q 暂停。'); continue
            s[key] = str(p.resolve()); save(statefile, s)
    while True:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('editor_preflight', ROOT/'tools/editor_preflight.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.validate_editor(Path(s['unity']))
            break
        except ValueError as error:
            print(error)
            selected = path_input('安装正确版本和组件后，请重新拖入 Unity.app/Contents/MacOS/Unity；q 暂停', s['unity'])
            s['unity'] = str(selected.resolve()); s.pop('license_confirmed', None); save(statefile, s)
    if not s.get('license_confirmed'):
        answer = ask('请在 Unity Hub 确认编辑器和 Mac 构建支持已安装，许可已激活。完成后输入 done（本程序不会替你接受条款）')
        if answer.lower() not in {'done', '完成', '已完成'}: raise Paused()
        s['license_confirmed'] = True; save(statefile, s)
    if 'textures' not in s:
        s['textures'] = ask('是否应用原版纹理字节恢复以节省内存？保持尺寸、mipmap 和模型，额外保留原构建。y/n', 'y').lower() in {'y', 'yes', '是'}
        save(statefile, s)

def prerequisites(s, check_editor=True):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('目前仅验证 Apple Silicon Mac；此机器平台尚不支持。')
    if sys.version_info[:2] != (3, 12):
        raise ValueError('请使用 Python 3.12 运行。安装后：python3.12 -m venv ~/.dsp-port-venv，然后用该环境的 Python 安装 requirements.txt 并启动向导。')
    for package, version in [('UnityPy', '1.25.4'), ('PyYAML', '6.0.3')]:
        try: installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: installed = None
        if installed != version:
            raise ValueError('Python 依赖缺失或版本不符。请在终端执行：\n' + shlex.join([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT/'requirements.txt')]))
    if not shutil.which('codesign'): raise ValueError('缺少 codesign，请安装 Apple 开发工具。')
    if not shutil.which('xcrun') or subprocess.run(['xcrun', '--find', 'clang'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise ValueError('缺少 Apple C 编译器。请在终端执行 xcode-select --install，或在 Xcode 中完成首次组件安装及本人许可确认；完成后回车重新检查。')
    if check_editor and s.get('unity'):
        import importlib.util
        spec = importlib.util.spec_from_file_location('editor_preflight', ROOT/'tools/editor_preflight.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.validate_editor(Path(s['unity']))
    if s.get('game'):
        dll = Path(s['game'])/'DSPGAME_Data/Managed/Assembly-CSharp.dll'
        if not dll.is_file() or hashlib.sha256(dll.read_bytes()).hexdigest() != SUPPORTED_SHA:
            raise ValueError('输入游戏文件已改变或不可用；请恢复同一已验证版本。')
    if s.get('workspace'):
        p = Path(s['workspace'])
        safe_private(p, s.get('game'))
        while not p.exists(): p = p.parent
        if shutil.disk_usage(p).free < 10*1024**3:
            raise ValueError('可用空间不足 10 GiB；请释放空间后继续。首次全流程建议至少 50 GiB。')

def command_for(step, s, app):
    ws = Path(s['workspace']); base = [sys.executable, str(ROOT/'port.py')]
    if step == 'prepare':
        return base + ['prepare', '--game', s['game'], '--workspace', str(ws), '--assetripper', s['assetripper'], '--spirv-cross', s['spirv_cross'], '--vkd3d', s['vkd3d']]
    if step == 'recover-shaders': return base + ['recover-shaders', '--workspace', str(ws)]
    if step == 'build':
        return base + ['build', '--project', str(ws/'work/dsp-runtime/port-project'), '--output', str(app), '--unity', s['unity'], '--release']
    return [sys.executable, str(ROOT/'tools/restore_original_textures.py'), '--game', s['game'], '--app', s['build_app'], '--output', str(app), '--report', str(app.with_suffix('.textures.json'))]

def run_pipeline(s, statefile, runner=subprocess.run):
    ws = Path(s['workspace']); logs = statefile.parent/'logs'; logs.mkdir(exist_ok=True)
    if 'prepare' in s.get('completed', []) and not (ws/'work/dsp-runtime/port-project').is_dir():
        raise ValueError('已完成的工程目录丢失，请恢复目录；不会把缺少工程当作完成。')
    for key in ('build_app', 'app'):
        if s.get(key) and not (Path(s[key])/'Contents/Info.plist').is_file():
            raise ValueError('已完成的 App 不存在：' + s[key])
    for step in STEPS:
        if step in s.get('completed', []):
            print('已完成，跳过：', step); continue
        if step == 'textures' and not s['textures']: continue
        # prepare is not transactional. Preserve a failed workspace before restarting it.
        if step == 'prepare' and ws.exists():
            cs = ws/'conversion-state.json'
            if cs.exists() and json.loads(cs.read_text()).get('stage') in {'platform_prepared', 'shader_recovery_failed', 'shaders_recovered'}:
                s.setdefault('completed', []).append(step); save(statefile, s); continue
            print('上次准备阶段中断。需要保留整个失败目录，再重新导出。不会删除已有文件。')
            if ask('输入 retry 将失败目录改名保留，并重试；q 暂停') != 'retry': raise Paused()
            ws.rename(ws.with_name(ws.name + '.interrupted-' + str(time.time_ns())))
        if step == 'recover-shaders':
            cs = ws/'conversion-state.json'
            if cs.exists() and json.loads(cs.read_text()).get('stage') == 'shaders_recovered':
                s.setdefault('completed', []).append(step); save(statefile, s); continue
        attempt = s.setdefault('attempts', {}).get(step, 0) + 1
        s['attempts'][step] = attempt
        app = ws/'build'/f'DSPMac-{step}-{attempt}.app'
        s['active'] = step; s['status'] = 'running'; save(statefile, s)
        log = logs/f'{step}-{attempt}.log'
        print(f'正在执行 {step}；可能耗时较长。日志：{log}', flush=True)
        try:
            with log.open('w') as out:
                runner(command_for(step, s, app), stdout=out, stderr=subprocess.STDOUT, check=True)
        except (Exception, KeyboardInterrupt) as e:
            s['status'] = 'interrupted' if isinstance(e, KeyboardInterrupt) else 'failed'
            s['failure_log'] = str(log); save(statefile, s)
            print(log.read_text(errors='replace')[-5000:])
            print('阶段未通过，没有标记完成。请检查日志；若是 Unity 登录/许可/组件问题，在 Hub 完成后重新运行向导。')
            raise Paused()
        if step == 'build': s['build_app'] = str(app); s['app'] = str(app)
        if step == 'textures': s['app'] = str(app)
        s.setdefault('completed', []).append(step); s['status'] = 'ready'; save(statefile, s)
    # A resumed completed pipeline must not erase its verified/failed test status.
    # Only a result explicitly tied to this output may survive a build change.
    result = s.get('smoke_result', {})
    phase = result.get('phase')
    if phase in {'passed', 'failed'} and s.get('smoke_app') == s.get('app'):
        s['status'] = 'smoke_' + phase
    elif s.get('smoke_armed_at') and s.get('smoke_app') == s.get('app') and not result:
        s['status'] = 'awaiting_smoke_result'
    else:
        for key in ('smoke_result', 'smoke_app', 'smoke_armed_at'):
            s.pop(key, None)
        s['status'] = 'built_needs_playtest'
    s['active'] = None; save(statefile, s)
    print('\n构建完成并通过本地签名检查：', s['app'])
    print('构建成功不代表所有游戏功能验证完成。下一步可以手动试玩，或执行一次静音保存/重载自检。')


def inspect_smoke_log(text, app):
    """Match the runtime to the selected app and reject native skipped draws."""
    match = re.search(r"^Mono path\[0\] = '(.+)'$", text, re.MULTILINE)
    expected = Path(app).resolve()/'Contents/Resources/Data/Managed'
    if not match or Path(match.group(1)).resolve() != expected:
        return 'wrong_app', []
    failures = [line for line in text.splitlines()
                if 'Skipping draw calls' in line or 'Shader error in ' in line
                or 'Failed to create pipeline state' in line
                or 'Screen position out of view frustum' in line
                or 'IndexOutOfRangeException:' in line or 'NullReferenceException:' in line
                or 'Assertion failed' in line]
    if failures:
        return 'failed', failures[:20]
    if 'DSP_MAC_SHUTDOWN_DRAINED' not in text or 'UIRunner.HandleApplicationQuit()' not in text:
        return 'waiting_for_exit', []
    return 'passed', []

def smoke(s, statefile):
    folder = Path.home()/'Library/Application Support/LocalDSPPort/DSPMacDevelopment'
    report = folder/'converter-smoke-result.json'
    if not s.get('smoke_armed_at'):
        if ask('可选自检会新建测试存档、正常退出并可能更新“最后退出”自动存档。请先正常退出所有 DSP 实例。输入 test 开始；回车跳过') != 'test': return
        subprocess.run([sys.executable, str(ROOT/'port.py'), 'arm-smoke'], check=True)
        s['smoke_armed_at'] = time.time(); s['smoke_app'] = s['app']; save(statefile, s)
    print('请在 Finder 打开这个 App：', s['app'])
    print('如 macOS 要求允许打开，请自行核对本地生成的 App；向导不会绕过系统安全设置。等待它静音测试并正常退出。')
    while True:
        answer = ask('正常退出后回车检查结果；若闪退输入 crash；q 暂停')
        if answer.lower() == 'crash':
            s['smoke_result'] = {'phase': 'failed', 'reason': 'user_reported_crash'}
            s['smoke_app'] = s['app']
            s['status'] = 'smoke_failed'; save(statefile, s)
            print('已记录闪退，验证未通过。请保留 Player.log 和 macOS 崩溃报告供排查，不要发布为可玩版本。')
            return
        flag = folder/'port-converter-smoke.flag'
        if flag.exists() or not report.exists() or report.stat().st_mtime < s['smoke_armed_at']:
            print('尚未检测到本次测试结果，请确认打开的是刚生成的 App。'); continue
        r = json.loads(report.read_text())
        if r.get('phase') not in {'passed', 'failed'}:
            print('测试仍在运行：', r.get('phase')); continue
        logfile = Path.home()/'Library/Logs/LocalDSPPort/DSPMacDevelopment/Player.log'
        if not logfile.exists() or logfile.stat().st_mtime < s['smoke_armed_at']:
            print('尚未检测到本次运行日志；不会仅凭旧 JSON 判定通过。'); continue
        logstatus, failures = inspect_smoke_log(logfile.read_text(errors='replace'), s['app'])
        if logstatus == 'wrong_app':
            for key in ('smoke_armed_at', 'smoke_app'):
                s.pop(key, None)
            s['status'] = 'built_needs_playtest'; save(statefile, s)
            raise ValueError('运行日志来自另一个 App。请重新运行向导并选择 test，再打开指定的新 App；这次结果未被接受。')
        crashes = Path.home()/'Library/Logs/DiagnosticReports'
        recent_crashes = [p.name for p in crashes.glob('DSPMacDevelopment-*.ips')
                          if p.stat().st_mtime >= s['smoke_armed_at']]
        if recent_crashes:
            failures.extend('本次测试时间范围内的系统崩溃报告：' + name for name in recent_crashes)
        if failures:
            r = dict(r, phase='failed', nativeLogErrors=failures)
        elif logstatus == 'waiting_for_exit':
            print('保存/重载已结束，但尚未确认正常退出。请等待自动退出后重试；若已闪退请输入 crash。'); continue
        s['smoke_result'] = r; s['smoke_app'] = s['app']; s['status'] = 'smoke_' + r['phase']; save(statefile, s)
        print('基础自检结果：', r['phase'], '\n详细结果：', report)
        print('还需手动检查画面、键鼠、旧存档和长时间游戏；不等于 Windows 全功能一致。')
        return

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session', type=Path, default=DEFAULT_SESSION, help='private checkpoint JSON, outside port-tools')
    a = p.parse_args(); statefile = a.session.expanduser().absolute(); safe_private(statefile)
    statefile.parent.mkdir(parents=True, exist_ok=True)
    with statefile.with_suffix('.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: print('该迁移会话已在运行，请回到原终端。'); return 1
        s = json.loads(statefile.read_text()) if statefile.exists() else {'schema': 1, 'completed': [], 'tool_fingerprint': fingerprint()}
        instructions(); print('进度文件：', statefile)
        try:
            if s['tool_fingerprint'] != fingerprint():
                raise ValueError('工具代码已变化，不能混用旧阶段。请用 --session 指定新的进度文件和新工作目录；旧文件保留。')
            while True:
                try: prerequisites(s, check_editor=False); break
                except ValueError as e: print(e); ask('完成上述操作后回车重新检查，q 暂停')
            configure(s, statefile)
            while True:
                try: prerequisites(s); break
                except ValueError as e: print(e); ask('完成后回车重新检查，q 暂停')
            if not s.get('confirmed'):
                print('游戏：', s['game'], '\n私有工作目录：', s['workspace'])
                if ask('准备完成。输入 start 开始自动导出、适配和构建；q 暂停') != 'start': raise Paused()
                s['confirmed'] = True; save(statefile, s)
            run_pipeline(s, statefile)
            if not s.get('smoke_result'): smoke(s, statefile)
            return 0
        except Paused:
            save(statefile, s); print('已保留进度。重新运行相同命令即可继续。'); return 2
        except (ValueError, OSError, KeyError, json.JSONDecodeError) as e:
            print('无法继续：', e); print('未删除任何输入或产物。'); return 1

if __name__ == '__main__':
    sys.exit(main())
