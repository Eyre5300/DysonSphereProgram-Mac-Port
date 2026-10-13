#!/bin/bash
set -e
cd "$(dirname "$0")"
converter_python="$HOME/.dsp-port-venv/bin/python"
if [ ! -x "$converter_python" ]; then
  if ! command -v python3.12 >/dev/null 2>&1; then
    echo '请先安装 Python 3.12。然后再次运行本入口。'
    exit 1
  fi
  python3.12 -m venv "$HOME/.dsp-port-venv"
fi
"$converter_python" -m pip install -r requirements.txt -r ipad/requirements.txt
if [ "$#" -eq 0 ]; then
  "$converter_python" ipad/source/migrate.py --config "$HOME/.dsp-port-ipad.json" --configure
else
  "$converter_python" ipad/source/migrate.py "$@"
fi
