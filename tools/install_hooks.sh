#!/bin/zsh
# 把 pre-commit 钩子指向 tools/ci.sh --fast
cd "$(dirname "$0")/.."
printf '#!/bin/zsh\nexec tools/ci.sh --fast\n' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit tools/ci.sh
echo "已安装：.git/hooks/pre-commit → tools/ci.sh --fast"
