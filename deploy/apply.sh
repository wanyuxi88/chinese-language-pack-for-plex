#!/bin/sh
# ============================================================
# Plex 简体中文语言包 · 容器内应用脚本
#
# 作用：把 /zh-pack 目录下的 zh.json 和 plex.mo 写入当前 Plex
#       版本对应的资源目录。幂等——内容相同则跳过，可反复执行。
#
# 用法：
#   宿主机：docker exec <容器名> /zh-pack/apply.sh
#   容器内：sh /zh-pack/apply.sh
#
# 环境变量（一般无需设置）：
#   ZH_PACK_SRC  语言包源目录，默认 /zh-pack
#   PLEX_ROOT    Plex 安装根目录，默认 /usr/lib/plexmediaserver
# ============================================================
set -u

SRC="${ZH_PACK_SRC:-/zh-pack}"
PLEX_ROOT="${PLEX_ROOT:-/usr/lib/plexmediaserver}"
CHANGED=0
FAILED=0

log() { echo "[zh-pack] $*"; }

deploy_file() {
	_src="$1"
	_dst="$2"
	_label="$3"

	if [ ! -f "$_src" ]; then
		log "跳过 ${_label}：缺少源文件 ${_src}"
		return 0
	fi
	if [ ! -f "$_dst" ]; then
		log "跳过 ${_label}：目标不存在（Plex 版本目录可能已变化）"
		return 0
	fi
	if cmp -s "$_src" "$_dst"; then
		log "${_label} 已是最新，无需处理"
		return 0
	fi

	_owner=$(stat -c '%u:%g' "$_dst" 2>/dev/null || echo 0:0)
	_mode=$(stat -c '%a' "$_dst" 2>/dev/null || echo 644)
	_tmp="${_dst}.zhpack.$$"

	if ! cp "$_src" "$_tmp" 2>/dev/null; then
		log "失败 ${_label}：无法写入目标目录（是否被只读映射？）"
		FAILED=$((FAILED + 1))
		return 1
	fi
	chown "$_owner" "$_tmp" 2>/dev/null || true
	chmod "$_mode" "$_tmp" 2>/dev/null || true
	if mv -f "$_tmp" "$_dst" 2>/dev/null; then
		log "${_label} 已更新 -> ${_dst}"
		CHANGED=$((CHANGED + 1))
	else
		rm -f "$_tmp" 2>/dev/null || true
		log "失败 ${_label}：替换失败（目录只读）"
		FAILED=$((FAILED + 1))
	fi
	return 0
}

log "Plex 根目录：${PLEX_ROOT}"
log "语言包目录：${SRC}"

# 1) 服务器端译文：路径与版本无关，稳定存在
deploy_file "${SRC}/plex.mo" \
	"${PLEX_ROOT}/Resources/locale/zh_CN/LC_MESSAGES/plex.mo" \
	"服务器端 plex.mo"

# 2) Web 端译文：位于 Plug-ins-<哈希> 目录，随 Plex 版本变化，遍历所有匹配项
for _dir in "${PLEX_ROOT}"/Resources/Plug-ins-*/WebClient.bundle/Contents/Resources/translations; do
	[ -d "$_dir" ] || continue
	deploy_file "${SRC}/zh.json" "${_dir}/zh.json" "Web 端 zh.json"
done

# 3) Web 端译文：部分版本使用无 .bundle 后缀的目录结构，一并兼容
for _dir in "${PLEX_ROOT}"/Resources/Plug-ins-*/WebClient/translations; do
	[ -d "$_dir" ] || continue
	deploy_file "${SRC}/zh.json" "${_dir}/zh.json" "Web 端 zh.json（旧结构）"
done

if [ "$FAILED" -gt 0 ]; then
	log "完成，但有 ${FAILED} 项失败"
	exit 1
fi
if [ "$CHANGED" -gt 0 ]; then
	log "完成，已更新 ${CHANGED} 个文件，重启 Plex 或强制刷新浏览器即可看到中文"
else
	log "完成，全部文件已是最新"
fi
exit 0
