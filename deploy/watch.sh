#!/bin/sh
# ============================================================
# Plex 简体中文语言包 · 容器内看护进程
#
# 由 hook.sh 在容器启动时以独立会话启动，常驻容器内部。
# 作用：LSIO 镜像可能在容器启动之后才自动升级 Plex，
#       从而把 Plug-ins-<哈希> 换成新目录；本进程定期复查并
#       把语言包补到当前版本目录，保证始终生效。
#
# 只读宿主机，只写容器内文件，不依赖任何宿主机服务。
# ============================================================
INTERVAL="${ZH_PACK_INTERVAL:-300}"
PACK_DIR="${ZH_PACK_SRC:-/zh-pack}"

while :; do
	sleep "$INTERVAL"
	[ -f "${PACK_DIR}/apply.sh" ] && /bin/sh "${PACK_DIR}/apply.sh" >/dev/null 2>&1
done
