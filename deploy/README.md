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

因此本方案用两层配合：

1. **宿主机目录持久化**：`zh.json`、`plex.mo` 存在宿主机，容器怎么删都在。
2. **启动钩子**：容器每次启动时（早于 Plex 服务）自动扫描当前版本的
   `Plug-ins-*` 目录，把宿主机上的 `zh.json` 写进去。升级后哈希变了也能自动命中。

`plex.mo` 因为是固定路径，额外用**单文件映射**兜底，连钩子都不依赖。

## 二、一条命令装好

把仓库放到飞牛上（或 `git clone`），然后：

```bash
cd chinese-language-pack-for-plex/deploy
sh install.sh                              # 默认容器名 plex
sh install.sh -c plex -d /vol1/1000/docker/plex/zh-pack   # 自定义
```

脚本会：

1. 建目录、复制 `zh.json` / `plex.mo` / `apply.sh` / `hook.sh`
2. 探测容器用的初始化系统，决定钩子映射到哪个目录：
   - Plex 官方镜像（s6-overlay v2）→ `/etc/cont-init.d/99-zh-pack`
   - linuxserver 镜像 → `/custom-cont-init.d/99-zh-pack`
   - 其它 → 不挂钩子，改用计划任务兜底
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

- 映射和钩子都在宿主机上，**重建容器后自动生效**，无需操作。
- 万一某版本钩子没跑（容器初始化系统变化），一条命令兜底：

```bash
docker exec plex sh /zh-pack/apply.sh && docker restart plex
```

- 想更保险，在飞牛「计划任务」里加一条定时兜底（幂等，内容相同不会重复写）：

```bash
docker exec plex sh /zh-pack/apply.sh >/dev/null 2>&1
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
| `hook.sh` | 容器启动钩子，调用 `apply.sh`，失败不阻断 Plex 启动 |
| `docker-compose.zh-pack.yml` | `install.sh` 生成，包含本机实际路径 |

> 注意：钩子脚本必须以 **LF** 换行保存（仓库已用 `.gitattributes` 固定），
> 若手工复制到 Windows 再上传导致 CRLF，`sh` 会报 `not found` 错误。
