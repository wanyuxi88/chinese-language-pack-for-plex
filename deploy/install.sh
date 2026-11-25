#!/bin/sh
# ============================================================
# Plex 简体中文语言包 · 飞牛（fnOS）宿主机安装脚本
#
# 做四件事：
#   1. 在宿主机建立语言包目录并放入 zh.json / plex.mo
#   2. 探测 Plex 容器的初始化系统，决定启动钩子的映射目标
#   3. 生成可直接使用的 docker-compose 覆盖文件（不修改你原有配置）
#   4. 若容器已挂载 /zh-pack，则立即应用一次并校验结果
#
# 用法（在宿主机 SSH 中执行）：
#   sh install.sh                       # 默认容器名 plex
#   sh install.sh -c plex -d /vol1/1000/docker/plex/zh-pack
#
# 参数：
#   -c  容器名             默认 plex
#   -d  宿主机语言包目录   默认 /vol1/1000/docker/plex/zh-pack
#   -s  语言包源目录       默认为本脚本所在仓库根目录
# ============================================================
set -u

CONTAINER="plex"
PACK_DIR="/vol1/1000/docker/plex/zh-pack"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SRC_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)

while getopts "c:d:s:h" opt; do
	case "$opt" in
		c) CONTAINER="$OPTARG" ;;
		d) PACK_DIR="$OPTARG" ;;
		s) SRC_DIR="$OPTARG" ;;
		h)
			sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
			exit 0
			;;
		*) exit 2 ;;
	esac
done

info() { echo "[安装] $*"; }
warn() { echo "[注意] $*"; }
die() { echo "[错误] $*" >&2; exit 1; }

# ---------- 0. 环境检查 ----------
command -v docker >/dev/null 2>&1 || die "未找到 docker 命令，请确认在宿主机上执行"
docker inspect "$CONTAINER" >/dev/null 2>&1 || die "找不到容器 ${CONTAINER}，请用 -c 指定正确的容器名（docker ps 可查看）"

[ -f "${SRC_DIR}/Web Clients/zh.json" ] || die "在 ${SRC_DIR} 下找不到 Web Clients/zh.json，请用 -s 指定仓库根目录"
[ -f "${SRC_DIR}/Plex Media Server/plex.mo" ] || die "在 ${SRC_DIR} 下找不到 Plex Media Server/plex.mo"

PLEX_ROOT=$(docker exec "$CONTAINER" sh -c 'test -d /usr/lib/plexmediaserver && echo /usr/lib/plexmediaserver || echo ""' 2>/dev/null)
[ -n "$PLEX_ROOT" ] || die "容器内未找到 /usr/lib/plexmediaserver，这不像 Plex 官方镜像，请确认容器"

# ---------- 1. 建立语言包目录 ----------
info "创建语言包目录：${PACK_DIR}"
mkdir -p "${PACK_DIR}" || die "无法创建 ${PACK_DIR}"

cp -f "${SCRIPT_DIR}/apply.sh" "${PACK_DIR}/apply.sh"
cp -f "${SCRIPT_DIR}/hook.sh" "${PACK_DIR}/hook.sh"
cp -f "${SCRIPT_DIR}/watch.sh" "${PACK_DIR}/watch.sh"
cp -f "${SRC_DIR}/Web Clients/zh.json" "${PACK_DIR}/zh.json"
cp -f "${SRC_DIR}/Plex Media Server/plex.mo" "${PACK_DIR}/plex.mo"
chmod 755 "${PACK_DIR}/apply.sh" "${PACK_DIR}/hook.sh" "${PACK_DIR}/watch.sh"
chmod 644 "${PACK_DIR}/zh.json" "${PACK_DIR}/plex.mo"
info "已复制 zh.json（$(wc -c < "${PACK_DIR}/zh.json") 字节）、plex.mo（$(wc -c < "${PACK_DIR}/plex.mo") 字节）"

# ---------- 2. 探测镜像与初始化系统 ----------
IMAGE=$(docker inspect -f '{{.Config.Image}}' "$CONTAINER" 2>/dev/null)

case "$IMAGE" in
	*linuxserver*)
		# linuxserver 镜像的 /custom-cont-init.d 默认可能不存在，
		# 添加映射时 Docker 会自动创建该目录，无需预先存在。
		HOOK_TARGET="/custom-cont-init.d/99-zh-pack"
		HOOK_DESC="linuxserver 镜像（/custom-cont-init.d）"
		;;
	*)
		if docker exec "$CONTAINER" test -d /etc/cont-init.d 2>/dev/null; then
			HOOK_TARGET="/etc/cont-init.d/99-zh-pack"
			HOOK_DESC="s6-overlay v2（/etc/cont-init.d）"
		elif docker exec "$CONTAINER" test -d /etc/s6-overlay/s6-rc.d 2>/dev/null; then
			HOOK_TARGET=""
			HOOK_DESC="s6-overlay v3（无通用自定义入口，改用定时器兜底）"
		elif docker exec "$CONTAINER" test -d /custom-cont-init.d 2>/dev/null; then
			HOOK_TARGET="/custom-cont-init.d/99-zh-pack"
			HOOK_DESC="自定义 init 目录（/custom-cont-init.d）"
		else
			HOOK_TARGET=""
			HOOK_DESC="未识别的初始化系统（改用定时器兜底）"
		fi
		;;
esac

info "镜像：${IMAGE}"
info "容器初始化系统：${HOOK_DESC}"

# ---------- 3. 生成覆盖文件 ----------
OVERRIDE="${PACK_DIR}/docker-compose.zh-pack.yml"
MO_PATH="${PLEX_ROOT}/Resources/locale/zh_CN/LC_MESSAGES/plex.mo"

{
	echo "# 由 install.sh 自动生成，供 docker compose 覆盖使用"
	echo "# 用法：docker compose -f <你原有的 compose 文件> -f ${OVERRIDE} up -d"
	echo "services:"
	echo "  ${CONTAINER}:"
	echo "    volumes:"
	echo "      # 语言包目录（宿主机持久化，镜像升级不会丢失）"
	echo "      - ${PACK_DIR}:/zh-pack:ro"
	if [ -n "$HOOK_TARGET" ]; then
		echo "      # 启动钩子：每次容器启动自动重新应用语言包"
		echo "      - ${PACK_DIR}/hook.sh:${HOOK_TARGET}:ro"
	fi
	echo "      # 服务器端译文：路径与版本无关，直接映射，永久生效"
	echo "      - ${PACK_DIR}/plex.mo:${MO_PATH}:ro"
} > "$OVERRIDE"

info "已生成：${OVERRIDE}"

# ---------- 4. 若已挂载则立即应用 ----------
if docker exec "$CONTAINER" test -d /zh-pack 2>/dev/null; then
	info "检测到容器已挂载 /zh-pack，立即应用："
	docker exec "$CONTAINER" sh /zh-pack/apply.sh
	info "重启容器使服务器端译文生效：docker restart ${CONTAINER}"
else
	warn "容器尚未挂载 /zh-pack，需要先添加映射并重建容器（见下方步骤）"
fi

# ---------- 5. 输出操作指引 ----------
cat <<EOF

============================================================
下一步：把下面三个映射加进你的容器，然后重建容器
============================================================

方式 A｜docker compose（推荐）
  1) 把你原有 compose 里的 volumes 增加以下内容
     （或直接用生成的覆盖文件一起启动）：

     volumes:
       - ${PACK_DIR}:/zh-pack:ro
$( [ -n "$HOOK_TARGET" ] && echo "       - ${PACK_DIR}/hook.sh:${HOOK_TARGET}:ro
       # ↑ 启动钩子，容器每次启动自动应用语言包（升级后不丢）" )
       - ${PACK_DIR}/plex.mo:${MO_PATH}:ro
       # ↑ 服务器端译文，路径固定，永久生效

  2) 重建容器：
     docker compose -f docker-compose.yml -f ${OVERRIDE} up -d

方式 B｜飞牛 Docker 图形界面
  容器 → ${CONTAINER} → 详情 → 存储/挂载 → 添加路径映射：
  $(printf '%-46s -> %s' "${PACK_DIR}" "/zh-pack（读写：否）")
$( [ -n "$HOOK_TARGET" ] && printf '  %-46s -> %s\n' "${PACK_DIR}/hook.sh" "${HOOK_TARGET}（读写：否）" )
  $(printf '%-46s -> %s' "${PACK_DIR}/plex.mo" "${MO_PATH}（读写：否）")
  保存后重启容器（飞牛会按新映射重建容器，设置不丢）

============================================================
验证
============================================================
  docker exec ${CONTAINER} sh /zh-pack/apply.sh     # 应显示「已是最新」
  docker exec ${CONTAINER} ls -l /usr/lib/plexmediaserver/Resources/locale/zh_CN/LC_MESSAGES/plex.mo
  docker exec ${CONTAINER} sh -c 'ls -l /usr/lib/plexmediaserver/Resources/Plug-ins-*/WebClient.bundle/Contents/Resources/translations/zh.json'
  浏览器访问 Plex → 强制刷新（Ctrl+Shift+R）→ 界面为简体中文
  「设置 → 关于」里的服务器端描述若为中文，说明 plex.mo 也已生效

============================================================
升级容器后
============================================================
  语言包文件在宿主机目录、映射写在 compose 里，拉新镜像重建容器后自动生效，
  宿主机上不需要安装任何服务或定时任务。

  启动钩子会顺带在容器内拉起一个看护进程（每 5 分钟复查），
  用于覆盖「Plex 在启动之后才自动升级、换掉 Plug-ins-<哈希> 目录」的情况。
  它只活在容器里，容器重建后由钩子自动重新拉起，不涉及宿主机。

  若某次钩子未生效，一条命令兜底：
    docker exec ${CONTAINER} sh /zh-pack/apply.sh && docker restart ${CONTAINER}

  查看看护进程是否在跑：
    docker exec ${CONTAINER} ps -eo pid,args | grep watch.sh

EOF
