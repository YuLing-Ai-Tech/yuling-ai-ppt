#!/usr/bin/env bash
# 本地 CI：--fast 给 pre-commit 用（行数 + 纯快测，不含 smoke 浏览器冒烟测试，Q-018）；
# 不带参数为全量（行数 + 全部非 slow 含 smoke + slow 回归；里程碑验收前必跑，输出贴进验收记录）
set -o pipefail
cd "$(dirname "$0")/.."
# 与回归基准同一套工具链（系统 python3 没装 playwright）
PY=(uv run --no-project --python 3.12 --with playwright==1.60.0 --with pillow==13.0.0 --with pytest==9.1.1 python)
echo "== 行数门禁"; "${PY[@]}" tools/check_line_limits.py || exit $?
if [[ "$1" == "--fast" ]]; then
  echo "== 快测（不含 smoke）"; "${PY[@]}" -m pytest -q -m "not slow and not smoke" || exit $?
  echo "CI（快）通过"; exit 0
fi
echo "== 快测（含 smoke）"; "${PY[@]}" -m pytest -q -m "not slow" || exit $?
echo "== 慢测（回归）"; "${PY[@]}" -m pytest -q -m slow || exit $?
echo "CI（全量）通过：$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M') 北京时间"
