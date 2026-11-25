#!/bin/sh
# ============================================================
# Plex 简体中文语言包 · 容器启动钩子
#
# 由容器初始化系统在每次启动时执行（早于 Plex 服务启动），
# 因此拉取新镜像重建容器后，中文语言包会自动重新应用，
# 无需手工干预。
#
# 兼容：
#   - linuxserver 镜像 ：映射到 /custom-cont-init.d/99-zh-pack
#   - s6-overlay v2    ：映射到 /etc/cont-init.d/99-zh-pack
#
# 全部逻辑只发生在容器内部，不修改宿主机任何系统配置。
# ============================================================

PACK_DIR="${ZH_PACK_SRC:-/zh-pack}"

# 1) 立即应用一次
if [ -f "${PACK_DIR}/apply.sh" ]; then
	/bin/sh "${PACK_DIR}/apply.sh" || echo "[zh-pack] 应用失败，可手动运行 docker exec <容器> sh /zh-pack/apply.sh 排查"
else
	echo "[zh-pack] 未找到 ${PACK_DIR}/apply.sh，跳过语言包应用"
fi

# 2) 拉起容器内看护进程，覆盖「Plex 在启动之后才自动升级、换掉哈希目录」的情况
#    用 pid 文件避免重复启动；进程随容器生命周期结束，不涉及宿主机。
if [ -f "${PACK_DIR}/watch.sh" ]; then
	PIDFILE=/tmp/zh-pack-watch.pid
	if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
		echo "[zh-pack] 看护进程已在运行（pid $(cat "$PIDFILE")）"
	elif command -v setsid >/dev/null 2>&1; then
		setsid /bin/sh "${PACK_DIR}/watch.sh" >/dev/null 2>&1 &
		echo $! > "$PIDFILE"
		echo "[zh-pack] 已在容器内启动看护进程（每 5 分钟复查一次）"
	else
		/bin/sh "${PACK_DIR}/watch.sh" >/dev/null 2>&1 &
		echo $! > "$PIDFILE"
		echo "[zh-pack] 已在容器内启动看护进程（每 5 分钟复查一次）"
	fi
fi

# 返回 0，避免因语言包问题阻断 Plex 容器启动
exit 0
