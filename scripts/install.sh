#!/usr/bin/env bash
# Standalone bootstrap for the shared transactional installer.
set -euo pipefail
fail() { printf 'Pantheon installer: %s\n' "$1" >&2; exit 1; }
case "$(uname -s)" in
  Darwin|Linux) ;;
  *) fail 'Use the native PowerShell installer on Windows.' ;;
esac
[ "$(id -u)" -ne 0 ] || fail 'Run as your normal user, without sudo.'
command -v git >/dev/null 2>&1 || fail 'Install Git first (macOS: xcode-select --install; Ubuntu: sudo apt install git).'
python_cmd=''
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(not ((3,10) <= sys.version_info[:2] <= (3,12)))' >/dev/null 2>&1; then
    python_cmd="$candidate"; break
  fi
done
[ -n "$python_cmd" ] || fail 'Install Python 3.10–3.12 first (macOS: brew install python@3.12; Ubuntu: sudo apt install python3 python3-venv).'
bootstrap=$(mktemp)
trap 'rm -f "$bootstrap"' EXIT
script_source=${BASH_SOURCE[0]:-}
local_bootstrap=''
if [ -n "$script_source" ]; then
  local_bootstrap="$(dirname "$script_source")/../pantheon/installer.py"
fi
if [ -n "$script_source" ] && [ -f "$script_source" ] && [ -f "$local_bootstrap" ]; then
  cp "$local_bootstrap" "$bootstrap"
elif [ -n "${PANTHEON_REPO_URL:-}" ] && [ -f "$PANTHEON_REPO_URL/pantheon/installer.py" ]; then
  cp "$PANTHEON_REPO_URL/pantheon/installer.py" "$bootstrap"
else
  command -v curl >/dev/null 2>&1 || fail 'Install curl first.'
  curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/pantheon/installer.py -o "$bootstrap"
fi
"$python_cmd" "$bootstrap" "$@"
