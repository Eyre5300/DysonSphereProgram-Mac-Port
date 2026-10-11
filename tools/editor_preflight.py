"""Validate the pinned local Unity installation without launching the editor."""
from pathlib import Path
import os
import plistlib

SUPPORTED_EDITOR = '2022.3.62f3c1'

def validate_editor(executable):
    executable = Path(executable).expanduser().resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError('未找到可执行的 Unity 编辑器。请在 Unity Hub 安装 Unity ' + SUPPORTED_EDITOR + '，并提供 Unity.app/Contents/MacOS/Unity 的路径。')
    contents = executable.parent.parent
    if executable.parent.name != 'MacOS' or contents.name != 'Contents':
        raise ValueError('请提供 Unity.app/Contents/MacOS/Unity 的路径。不能用 Unity Hub 或其他启动脚本代替编辑器。')
    try:
        info = plistlib.loads((contents / 'Info.plist').read_bytes())
    except (OSError, plistlib.InvalidFileException) as error:
        raise ValueError('Unity 安装元数据不可读，请在 Unity Hub 检查或重新安装编辑器。') from error
    version = info.get('CFBundleVersion')
    if version != SUPPORTED_EDITOR:
        raise ValueError('Unity 版本不匹配：检测到 ' + str(version) + '，当前转换仅验证 ' + SUPPORTED_EDITOR + '。请安装指定版本并重新选择路径；不会自动改写工程版本。')
    support = contents / 'PlaybackEngines/MacStandaloneSupport'
    if not support.is_dir():
        raise ValueError('Unity 缺少 Mac 构建支持。请在 Unity Hub 的该编辑器设置中安装 Mac Build Support，完成后回车重新检查。')
    return {'executable': str(executable), 'version': version, 'macBuildSupport': str(support)}
