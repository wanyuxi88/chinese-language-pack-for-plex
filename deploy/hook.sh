#!/bin/sh
# ============================================================
# Plex 简体中文语言包 · 容器启动钩子
#
# 由容器初始化系统在每次启动时执行（早于 Plex 服务启动），
# 因此拉取新镜像重建容器后，中文语言包会自动重新应用，
# 无需手工干预。
#
# 兼容：
#   - s6-overlay v2 ：映射到 /etc/cont-init.d/99-zh-pack
#   - linuxserver  ：映射到 /custom-cont-init.d/99-zh-pack
#
# 本脚本不依赖 /zh-pack/apply.sh 的可执行位（映射可能丢失权限），
# 统一用 /bin/sh 调用。
# ============================================================

PACK_DIR="${ZH_PACK_SRC:-/zh-pack}"

if [ -f "${PACK_DIR}/apply.sh" ]; then
	/bin/sh "${PACK_DIR}/apply.sh" || echo "[zh-pack] 启动钩子执行失败，请手动运行 apply.sh 查看原因"
else
	echo "[zh-pack] 未找到 ${PACK_DIR}/apply.sh，跳过语言包应用"
fi

# 返回 0，避免因语言包问题阻断 Plex 容器启动
exit 0
