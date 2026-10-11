#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ -x "$HOME/.dsp-port-venv/bin/python" ]; then
  converter_python="$HOME/.dsp-port-venv/bin/python"
elif command -v python3.12 >/dev/null 2>&1; then
  converter_python="$(command -v python3.12)"
else
  echo '请先安装 Python 3.12（https://www.python.org/downloads/macos/）。'
  echo '然后在本目录的终端运行：'
  echo 'python3.12 -m venv ~/.dsp-port-venv'
  echo '~/.dsp-port-venv/bin/python -m pip install -r requirements.txt'
  echo '安装后再次双击 start.command。完整步骤见 docs/用户操作指南.txt。'
  read -r -p '按回车关闭。' converter_reply
  exit 1
fi
"$converter_python" wizard.py "$@"
converter_status=$?
read -r -p '按回车关闭窗口。' converter_reply
exit "$converter_status"
