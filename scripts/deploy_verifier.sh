#!/bin/bash
set -euo pipefail

# 全量部署 verifier 代码到远端（docs/external-eval-deployment.md「更新代码」一节的封装）。
# 排除项锚定到仓库根：/impl/data（运行数据）、/.env（服务器专属配置）等绝不覆盖；
# 不锚定会误伤 impl/projects/*/investigation/*/experiments 等调查包冻结产物。
#
# 用法：
#   scripts/deploy_verifier.sh user@host [/opt/verifier] [--no-restart] [--dry-run]
#
# 默认部署后 ssh 执行 systemctl restart verifier；--no-restart 跳过。
# Windows 用户请在 WSL 里运行（依赖 bash/rsync/ssh）。

cd "$(dirname "$0")/.."

usage() {
  sed -n '3,13p' "$0" | sed 's/^# \{0,1\}//'
}

HOST=""
REMOTE_PATH="/opt/verifier"
RESTART=1
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --no-restart) RESTART=0;;
    --dry-run) DRY_RUN=1;;
    -h|--help) usage; exit 0;;
    -*) echo "未知参数: $arg" >&2; usage >&2; exit 1;;
    *)
      if [ -z "$HOST" ]; then HOST="$arg"
      else REMOTE_PATH="$arg"
      fi
      ;;
  esac
done

if [ -z "$HOST" ]; then
  echo "缺少远端主机（user@host）" >&2
  usage >&2
  exit 1
fi

RSYNC_ARGS=(-az)
[ "$DRY_RUN" = 1 ] && RSYNC_ARGS+=(-n -v)
RSYNC_ARGS+=(
  --exclude /.git
  --exclude /.env
  --exclude /tmp
  --exclude /experiments
  --exclude /issues
  --exclude /tests
  --exclude '__pycache__'
  --exclude /impl/data
)

rsync "${RSYNC_ARGS[@]}" ./ "$HOST:$REMOTE_PATH/"

if [ "$DRY_RUN" = 1 ]; then
  echo "dry-run 完成，未改动远端。"
  exit 0
fi

if [ "$RESTART" = 1 ]; then
  ssh "$HOST" 'systemctl restart verifier'
  echo "部署完成并已重启 verifier：$HOST:$REMOTE_PATH"
else
  echo "部署完成（未重启）：$HOST:$REMOTE_PATH"
fi
