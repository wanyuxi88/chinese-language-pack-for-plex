# Docker / 飞牛 fnOS 映射部署

把中文语言包放在**宿主机目录**里，通过路径映射喂给 Plex 容器。这样拉取新镜像、
重建容器时语言包都不会丢，也不需要每次升级后手工 `docker cp`。

## 一、为什么不能只做「文件映射」

Plex 的两个语言文件路径不一样：

| 文件 | 容器内路径 | 是否随版本变化 |
| --- | --- | --- |
| 服务器端 `plex.mo` | `/usr/lib/plexmediaserver/Resources/locale/zh_CN/LC_MESSAGES/plex.mo` | **不变**，可直接映射 |
| Web 端 `zh.json` | `/usr/lib/plexmediaserver/Resources/Plug-ins-<哈希>/WebClient.bundle/Contents/Resources/translations/zh.json` | **变**，目录名含版本哈希 |

`Plug-ins-b3b13e506` 这样的目录名每次 Plex 升级都会变。如果把 `zh.json` 映射到
某个固定哈希目录，升级后新版本读的是新哈希目录，映射就落在了一个不再被使用的
路径上——看起来"映射失效了"。

`plex.mo` 因为是固定路径，额外用**单文件映射**兜底，连钩子都不依赖。

三层保障，全部不涉及宿主机系统：

| 层 | 机制 | 覆盖的场景 |
| --- | --- | --- |
| 1 | `plex.mo` 单文件映射 | 服务器端译文，路径固定，永久生效 |
| 2 | `/custom-cont-init.d` 启动钩子 | 容器每次启动，把 `zh.json` 写入当时的 `Plug-ins-<哈希>` |
| 3 | 容器内 `watch.sh` 看护进程 | Plex 在启动之后才升级、哈希目录被换掉的情况 |

## 二、一条命令装好

把仓库放到飞牛上（或 `git clone`），然后：

```bash
cd chinese-language-pack-for-plex/deploy
sh install.sh                              # 默认容器名 plex
sh install.sh -c plex -d /vol1/1000/docker/plex/zh-pack   # 自定义
```

脚本会：

1. 建目录、复制 `zh.json` / `plex.mo` / `apply.sh` / `hook.sh` / `watch.sh`
2. 探测容器用的初始化系统，决定钩子映射到哪个目录：
   - Plex 官方镜像（s6-overlay v2）→ `/etc/cont-init.d/99-zh-pack`
   - linuxserver 镜像 → `/custom-cont-init.d/99-zh-pack`
   - 其它 → 不挂钩子，纯靠看护进程与手动应用
3. 生成 `docker-compose.zh-pack.yml` 覆盖文件（不碰你原有配置）
4. 打印需要添加的映射和验证命令

## 三、把三个映射加进容器

容器必须**重建**才能加映射。选一种方式：

### 方式 A：docker compose

在原有 compose 的 `volumes` 里增加（或直接用生成的覆盖文件）：

```yaml
services:
  plex:
    volumes:
      - /vol1/1000/docker/plex/zh-pack:/zh-pack:ro
      - /vol1/1000/docker/plex/zh-pack/hook.sh:/etc/cont-init.d/99-zh-pack:ro
      - /vol1/1000/docker/plex/zh-pack/plex.mo:/usr/lib/plexmediaserver/Resources/locale/zh_CN/LC_MESSAGES/plex.mo:ro
```

```bash
docker compose -f docker-compose.yml -f /vol1/1000/docker/plex/zh-pack/docker-compose.zh-pack.yml up -d
```

### 方式 B：飞牛 Docker 图形界面

容器 → plex → 详情 → 存储 / 挂载 → 添加路径映射（三条都设为只读）：

| 宿主机路径 | 容器内路径 |
| --- | --- |
| `/vol1/1000/docker/plex/zh-pack` | `/zh-pack` |
| `/vol1/1000/docker/plex/zh-pack/hook.sh` | `/etc/cont-init.d/99-zh-pack` |
| `/vol1/1000/docker/plex/zh-pack/plex.mo` | `/usr/lib/plexmediaserver/Resources/locale/zh_CN/LC_MESSAGES/plex.mo` |

保存后重启容器。**注意**：飞牛每次升级 Plex 镜像后会按原映射重建容器，映射会保留。

## 四、验证

```bash
# 1. 看应用日志，应为「已是最新」
docker exec plex sh /zh-pack/apply.sh

# 2. 确认文件确实替换进了当前版本目录
docker exec plex sh -c 'ls -l /usr/lib/plexmediaserver/Resources/Plug-ins-*/WebClient.bundle/Contents/Resources/translations/zh.json'

# 3. 浏览器强制刷新（Ctrl+Shift+R）看界面语言
```

服务器端 `plex.mo` 生效的标志是「设置 → 关于」里的描述文字变成中文。

## 五、升级容器之后

- 语言包文件在宿主机目录、映射写在 compose 里，**重建容器后自动生效**，无需操作。
- **宿主机上不需要安装任何服务或定时任务**。所有自动化都在容器内部完成（启动钩子
  + 看护进程），容器重建时由钩子自动重新拉起。
- 万一某版本钩子没跑（容器初始化系统变化），一条命令兜底：

```bash
docker exec plex sh /zh-pack/apply.sh && docker restart plex
```

### 为什么还需要看护进程

linuxserver 镜像的启动流程里，`init-custom-init`（执行自定义钩子的服务）与
`init-plex-update`（可能升级 Plex、换掉 `Plug-ins-<哈希>` 目录的服务）之间**没有强制
先后顺序**。也就是说存在这种情况：钩子把 `zh.json` 写进了当前哈希目录，随后 Plex 被
升级、目录换成了新的，译文又回到官方版本。

所以 `hook.sh` 在应用完之后，会在容器内拉起一个 `watch.sh` 看护进程，每 5 分钟复查
一次，发现哈希目录变了就补进去。它只读宿主机的映射目录、只写容器内文件，容器重启后
由钩子重新拉起，生命周期完全跟着容器走。

```bash
# 确认看护进程在跑
docker exec plex ps -eo pid,args | grep watch.sh
```

## 六、更新语言包内容

上游发布新版后，把新的 `zh.json`、`plex.mo` 覆盖到宿主机目录，然后：

```bash
docker exec plex sh /zh-pack/apply.sh && docker restart plex
```

`apply.sh` 用 `cmp` 比较内容，相同就跳过，可放心重复执行。

## 七、回滚

```bash
# 移除映射并重建容器即可完全恢复官方文件（镜像内文件从未被修改）
docker exec plex ls /usr/lib/plexmediaserver/Resources/locale/zh_CN/LC_MESSAGES/
```

因为所有改动都发生在容器可写层，且每次重建容器都会从镜像还原，删除映射后
就是官方原版。宿主机目录可以留着，下次再挂回来即可。

## 八、文件说明

| 文件 | 作用 |
| --- | --- |
| `install.sh` | 宿主机一键安装：建目录、探测钩子、生成 compose 覆盖 |
| `apply.sh` | 容器内执行的应用脚本，幂等，可重复运行 |
| `hook.sh` | 容器启动钩子，调用 `apply.sh` 并拉起看护进程，失败不阻断 Plex 启动 |
| `watch.sh` | 容器内看护进程，每 5 分钟复查哈希目录变化并补写译文 |
| `docker-compose.zh-pack.yml` | `install.sh` 生成，包含本机实际路径 |

## 九、对宿主机的改动范围

本方案**只在宿主机上做两件事**，都是映射方案本身必需的最小改动：

1. 新建一个存语言包的目录（默认 `/vol1/1000/docker/plex/zh-pack`）
2. 在 docker compose 里增加三条只读路径映射

**不会**安装 systemd 服务、不会加 cron / 计划任务、不会改系统配置。所有自动化
脚本都只在容器内部执行，容器删除后自动消失。

如果连目录也不想建在宿主机，可以把映射源指到已有目录，或改用「进容器直接替换文件」
的传统方式（只是每次升级都要重做一遍）。

## 十、linuxserver 镜像的注意事项

| 现象 | 说明 |
| --- | --- |
| 容器内没有 `/custom-cont-init.d` | 正常。挂载文件到该路径时 Docker 会自动创建目录，LSIO 自带的 `init-custom-files` 会执行其中的**可执行**文件 |
| 钩子提示 `is not an executable file` | 宿主机上的 `hook.sh` 丢了可执行位，`chmod 755` 即可 |
| 升级镜像后译文变回英文 | `init-plex-update` 改了 `Plug-ins-<哈希>` 目录，等看护进程 5 分钟内自动修正，或手动 `docker exec plex sh /zh-pack/apply.sh` |
| `/zh-pack` 里改文件后容器内没变 | `plex.mo` 是单文件映射，改完即生效；`zh.json` 需要重新 `apply.sh` 或等看护进程 |

> 注意：钩子脚本必须以 **LF** 换行保存（仓库已用 `.gitattributes` 固定），
> 若手工复制到 Windows 再上传导致 CRLF，`sh` 会报 `not found` 错误。
