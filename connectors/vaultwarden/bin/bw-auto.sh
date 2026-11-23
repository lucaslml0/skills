#!/usr/bin/env bash
# bw-auto.sh — Vaultwarden 全自动解锁包装器
#
# 用法:
#   bw-auto.sh status                          # 不用解锁也能看状态
#   bw-auto.sh list items --search google      # 自动解锁后跑 bw 命令
#   bw-auto.sh get password google1
#   bw-auto.sh sync
#   bw-auto.sh lock                            # 锁 vault，并丢弃缓存的 session
#   bw-auto.sh forget                          # 锁 vault + 删 session 缓存 + 清空 bw.env 里的密码
#
# 机制（按顺序，只走第一条能走通的）:
#   1. 读 ~/workspace/.credentials/bw-session 里的 BW_SESSION，
#      用 `bw unlock --check --session <key>` 验一下，还有效就直接用，
#      全程不碰主密码。
#   2. session 失效/没有时，读 ~/workspace/bw.env 里的 BW_PASSWORD，
#      用 `bw unlock --passwordenv BW_PASSWORD --raw` 拿一个新 session，
#      立刻 unset BW_PASSWORD，再把新 session（不是主密码）写进
#      bw-session（600），下次接着用。
#   3. 两条都走不通就报错退出，不会用空密码重试，也不会把密码打进日志。
#
# 注意:
#   - bw unlock 会让旧 session 失效，所以每次重新解锁都会覆盖 bw-session。
#   - Secure Vault 里存的那条登录读不回明文，所以全自动走不了那条路，
#     只能走上面这个你自己填的 bw.env。
#   - 主密码只存在 bw.env 里（600），session 只存在 bw-session 里（600），
#     两个文件都不进 git、不进聊天、不进记忆。
set -euo pipefail

BW="/home/hatch/.local/bin/bw"
# 沙盒里跑的是 root，但家目录有两个：Kit 的 exec 里 HOME=/home/hatch，
# WebSSH 终端里以 root 登录后 HOME=/root。用 $HOME 找文件，在 WebSSH
# 终端里就会走到不存在的 /root/workspace。所以一律用 /home/hatch 为准，
# 只有它不存在时才退回 $HOME。
if [[ -d /home/hatch/workspace ]]; then
  BASE="/home/hatch"
else
  BASE="$HOME"
fi
# bw CLI 自己的登录状态也在 $HOME/.config/Bitwarden CLI 里，
# WebSSH root 终端里 HOME=/root 时它会以为没登录。所以这里也把
# HOME 指回 /home/hatch，让 bw 和脚本找的是同一套文件。
export HOME="$BASE"
ENV_FILE="$BASE/workspace/bw.env"
SESSION_FILE="$BASE/workspace/.credentials/bw-session"

export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"
export NODE_EXTRA_CA_CERTS="$BASE/workspace/vaultwarden-lucas-cert.pem"

usage() {
  echo "usage: bw-auto.sh <status|lock|forget|sync|list|get|create|edit|...> [args]" >&2
  echo "  例: bw-auto.sh list items --search google" >&2
  echo "      bw-auto.sh get password google1" >&2
  exit 2
}

# 拿一个可用的 session，放到 $SESSION 里；拿不到就报错退出。
ensure_session() {
  SESSION=""
  if [[ -s "$SESSION_FILE" ]]; then
    local cached
    cached="$(cat "$SESSION_FILE")"
    if [[ -n "$cached" ]] && "$BW" unlock --check --session "$cached" >/dev/null 2>&1; then
      SESSION="$cached"
      return 0
    fi
    rm -f "$SESSION_FILE"
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    echo "bw-auto: 找不到 $ENV_FILE，请先在里面填 BW_PASSWORD=" >&2
    return 1
  fi
  # 只读这个你自己写的文件；不 source 它，以免密码里的 $、`、\ 等
  # 被 shell 展开改掉。只取 BW_PASSWORD= 后面的原样内容，去掉首尾一对
  # 引号和行尾回车，读完立刻 unset，不留在环境里。
  BW_PASSWORD="$(grep '^BW_PASSWORD=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e "s/^'//" -e "s/'\$//" -e 's/^"//' -e 's/"$//')"
  export BW_PASSWORD
  if [[ -z "${BW_PASSWORD:-}" ]]; then
    echo "bw-auto: $ENV_FILE 里的 BW_PASSWORD 还是空的，填好主密码再跑" >&2
    unset BW_PASSWORD || true
    return 1
  fi
  SESSION="$("$BW" unlock --passwordenv BW_PASSWORD --raw)"
  unset BW_PASSWORD
  mkdir -p "$(dirname "$SESSION_FILE")"
  printf '%s' "$SESSION" > "$SESSION_FILE"
  chmod 600 "$SESSION_FILE"
}

[[ $# -ge 1 ]] || usage

case "$1" in
  status)
    exec "$BW" status
    ;;
  lock)
    "$BW" lock >/dev/null 2>&1 || true
    rm -f "$SESSION_FILE"
    echo "locked, session 已丢弃"
    ;;
  forget)
    "$BW" lock >/dev/null 2>&1 || true
    rm -f "$SESSION_FILE"
    cat > "$ENV_FILE" <<'EOF'
# Bitwarden / Vaultwarden 主密码，只填下面这一行，填完保存。
# 这个文件只在你自己的沙盒里，权限 600，不要发到聊天、不要提交到 git。
# Kit 只在 vault 需要解锁、且缓存的 session 失效时才读它，读完立刻 unset，不会把密码写进日志、记忆或别的文件。
# 想停用全自动时，把下面这行清空、或删掉这个文件，再跑一次 bw-auto.sh lock 即可。
BW_PASSWORD=
EOF
    chmod 600 "$ENV_FILE"
    echo "forgot: session 已删，bw.env 已清空回模板"
    ;;
  *)
    ensure_session
    export BW_SESSION="$SESSION"
    exec "$BW" "$@"
    ;;
esac
