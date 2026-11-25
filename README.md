# Chinese Language Pack for Plex

![verify](https://github.com/wanyuxi88/chinese-language-pack-for-plex/actions/workflows/verify.yml/badge.svg)

Plex 的本地化工作并不是由专业团队完成的，而是通过翻译平台 Transifex 的[公开项目](https://explore.transifex.com/plex-1/)，由各国的志愿者自发参与翻译完成的。参与翻译的人员比较比较多，构成复杂，翻译工作的时间跨度比较大，并且缺乏统一的管理和审核，目前，虽然汉化工作基本上已经完成，但是依然存在大量错误或者不恰当的翻译，整体汉化质量一般。

据我所知，Plex 的简体中文翻译板块已经很多年没有审核人员了，并且似乎也无法再进行申请（可能已经取消审核流程了）。早期的审核人员审核通过了很多错误的翻译，比如 “Studio（制片公司）” 被翻译为了 “演播室”，“Record Label（唱片公司）” 被翻译为了 “录音标签” 等等；目前使用的翻译还存在很多一词多译的情况，比如 “Artist” 同时存在 “艺人、艺术家、作者” 三种翻译，“Collection” 同时存在 “合集、收藏集、选集、收集” 四种翻译等等；此外，目前的翻译还存在很多语义表达上的问题，导致很多功能的描述虽然翻译为了中文，但是中文用户却难以理解其含义。

因为 Plex 是一个跨平台的应用服务，有很多内容需要分平台进行翻译，比如安卓端、苹果端、网页端、服务器等都有单独的翻译项目，对于未审核（未复核）的字符串，我们是可以自由进行翻译和修改的，但是已审核（已复核）的字符串我们就无权修改了，如上所述，有很多已审核的翻译是存在问题的，由于我们无权进行修改，通过官方渠道似乎没有什么办法干预，同时也因为未审核的字符串可以被随意修改，直接在官方项目上修改或提交翻译也可能被其他人再次改动，所以我决定自己建立一个 Plex 的翻译项目，按照我认为规范的方式对 Plex 进行汉化，并将汉化后的语言包共享给大家使用。

## 翻译进度
<img width="100%" alt="进度" src="https://github.com/user-attachments/assets/2fa985ad-3048-4aa4-913a-8ec3fbb5d466">

上图中蓝色的部分代表官方翻译的部分，绿色的部分代表我翻译的部分。其中对 Plex Media Server 的翻译将应用到全平台的 Plex、Plex Web、Plex HTPC、Plexamp 和 Plex Dash 等应用程序上，对 Web Clients 的翻译将应用到桌面端的 Plex 应用程序以及通过 IP 或自定义域名访问的 Plex Web（网页端）上。（翻译将持续更新）

当前进度（由 `tools/progress.py` 生成，随每次提交更新）：

<!-- progress:begin -->
| 语言文件 | 条目 | 已改写 | 沿用官方 | 完成度 |
|---|---:|---:|---:|---:|
| `Web Clients/zh.json` | 2913 | 1952 | 961 | **67.0%** |
| `Plex Media Server/plex.po` | 1216 | 682 | 534 | **56.1%** |
| 合计 | 4129 | 2634 | 1495 | **63.8%** |

> 统计口径：与新版本官方译文逐条比对，「已改写」= 与官方不同的条目。由 `tools/progress.py` 生成（基于 1.43.5.11079-b3b13e506），请勿手改。
<!-- progress:end -->


## 术语表与校验工具

上面提到的「一词多译」问题（Artist 有「艺人/艺术家/作者」、Collection 有「合集/收藏集/选集」等），现在由统一术语表约束。仓库里所有工具都只用 Python 标准库，无需安装依赖：

| 文件 | 作用 |
|---|---|
| [**GLOSSARY.md**](GLOSSARY.md) | 八大类术语（内容对象、播放与转码、直播录制、音乐、账户社交、服务器维护、动作动词、状态词），附格式规范、易混词对照和复审流程 |
| [`tools/glossary.json`](tools/glossary.json) | 机器可读的术语、禁用译法、例外白名单 |
| [`tools/consistency.json`](tools/consistency.json) | 跨端差异的豁免清单（同一英文键在 Web 与服务端允许不同译的语境词） |
| [`tools/gloss.py`](tools/gloss.py) | 术语巡检：禁用译法、半角标点、「你/您」、「此/该」 |
| [`tools/check.py`](tools/check.py) | 结构校验：占位符、空译文、首尾空白、重复键、po 与 mo 是否同步 |
| [`tools/upstream_diff.py`](tools/upstream_diff.py) | 升级比对：新版 Plex 出来后列出新增/消失条目，并给翻译记忆候选 |
| [`tools/progress.py`](tools/progress.py) | 生成本文开头的进度表 |
| [`tools/plexio.py`](tools/plexio.py) | 上面几个脚本共用的 JSON / po / mo 读写 |

```bash
python tools/check.py            # 提交前跑这个，退出码 0 才算过
python tools/check.py -v         # 连警告明细（新出现的跨端差异会在这里）
python tools/gloss.py            # 术语巡检；当前 0 命中
python tools/progress.py --write # 更新进度表
```

`.github/workflows/verify.yml` 在每次 push 和 PR 时自动跑 `check.py` 与 `gloss.py`，占位符丢失、mo 忘记编译、术语跑偏都会直接失败，不会合进主分支。

升级到新版 Plex 后：

```bash
python tools/upstream_diff.py --upstream /path/to/extracted --tm 3
python tools/progress.py --upstream /path/to/extracted --write
```

## 效果展示
以下为部分翻译内容对比，左侧为 Plex 官方版本，右侧为我的版本。下图使用的是 Plex for MacOS 客户端。

<img width="100%" alt="1" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/0e093536-2efa-4409-8584-93b0ec4a8f2f">

<img width="100%" alt="2" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/5cf76a03-aba3-45c2-83ba-fbbe22b3fed6">

<img width="100%" alt="3" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/8ccc25b1-56f4-4182-8616-d4a88a74a9ca">

<img width="100%" alt="4" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/500d8854-b4f9-4c75-8002-7a0b8fddb94c">

<img width="100%" alt="5" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/54f07a11-970b-4dd4-b3fd-854877dd2ff3">

<img width="100%" alt="6" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/e6dcc029-372b-4e67-b0a7-198eac310b02">

<img width="100%" alt="7" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/68bd76f2-8682-4e01-9749-10417c7a26b8">

<img width="100%" alt="8" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/f8bda678-b910-437a-8fe2-52dae65e4204">

<img width="100%" alt="9" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/6275a1db-904d-4f1e-bd9a-bfaa799be800">

<img width="100%" alt="10" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/1c80c81a-8864-4906-a53a-6df520edfd9a">

<img width="100%" alt="11" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/93cac18b-8c8a-4bc1-b5c8-9c1544b5e9af">

<img width="100%" alt="12" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/4689780d-9070-49bd-b02b-17583649980c">

<img width="100%" alt="13" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/bc185bea-fd4f-4239-a37e-3e8f35378f21">

<img width="100%" alt="14" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/76637d63-75e3-4071-ab00-4f21b41efb4d">

<img width="100%" alt="15" src="https://github.com/x1ao4/chinese-language-pack-for-plex/assets/112841659/6fddb59f-6679-498d-ae22-80e7b6c55e70">

## 支持平台
### Plex Desktop
- Plex for MacOS
- Plex for Windows
- Plex for Linux

### Plex Web
- 通过 IP 或自定义域名访问的 Plex 网页端

### Plex Media Server
- Plex Media Server for MacOS
- Plex Media Server for Windows
- Plex Media Server for Linux
- Plex Media Server for Docker
- Plex Media Server for NAS（套件）

## 使用方法
### Plex Desktop
请下载 Web Clients 文件夹内的 `zh.json` 文件，然后替换你的 Plex 目录中的 `zh.json` 文件，重启 Plex 客户端后即可生效（请确保文件的权限和模式与原文件一致）。你可以参考以下地址找到你的 `zh.json` 文件。
```
# MacOS
/Applications/Plex.app/Contents/Resources/web-client/translations/zh.json

# Windows
C:\Program Files\Plex\Plex\web-client\translations\zh.json
```

### Plex Web
请下载 Web Clients 文件夹内的 `zh.json` 文件，然后替换你的 Plex Media Server 目录中的 `zh.json` 文件，重启 Plex Media Server 后即可生效（请确保文件的权限和模式与原文件一致）。你可以参考以下地址找到你的 `zh.json` 文件。（`Plug-ins-c0dd5a73e` 会随着 Plex Media Server 的版本发生变化）
```
# MacOS
/Applications/Plex Media Server.app/Contents/Resources/Plug-ins-c0dd5a73e/WebClient.bundle/Contents/Resources/translations/zh.json

# Windows
C:\Program Files\Plex\Plex Media Server\Resources\Plug-ins-c0dd5a73e\WebClient.bundle\Contents\Resources\translations\zh.json

# Docker（容器内部目录）
/usr/lib/plexmediaserver/Resources/Plug-ins-c0dd5a73e/WebClient.bundle/Contents/Resources/translations/zh.json

# QNAP
/share/CACHEDEV1_DATA/.qpkg/PlexMediaServer/Resources/Plug-ins-c0dd5a73e/WebClient.bundle/Contents/Resources/translations/zh.json

# Synology
/volume1/@appstore/PlexMediaServer/Resources/Plug-ins-c0dd5a73e/WebClient.bundle/Contents/Resources/translations/zh.json
```

### Plex Media Server
请下载 Plex Media Server 文件夹内的 `plex.mo` 文件，然后替换你的 Plex Media Server 目录中的 `plex.mo` 文件，重启 Plex Media Server 后即可生效（请确保文件的权限和模式与原文件一致）。你可以参考以下地址找到你的 `plex.mo` 文件。
```
# MacOS
/Applications/Plex Media Server.app/Contents/Resources/locale/zh_CN/LC_MESSAGES/plex.mo

# Windows
C:\Program Files\Plex\Plex Media Server\Resources\locale\zh_CN\LC_MESSAGES/plex.mo

# Docker（容器内部目录）
/usr/lib/plexmediaserver/Resources/locale/zh_CN/LC_MESSAGES/plex.mo

# QNAP
/share/CACHEDEV1_DATA/.qpkg/PlexMediaServer/Resources/locale/zh_CN/LC_MESSAGES/plex.mo

# Synology
/volume1/@appstore/PlexMediaServer/Resources/locale/zh_CN/LC_MESSAGES/plex.mo
```

## Docker 映射部署（推荐，升级容器不丢）

上面这种「进容器替换文件」的方式，每次升级镜像重建容器都会失效。如果你的 Plex 跑在
Docker（含飞牛 fnOS、群晖、威联通）里，建议改用 `deploy/` 下的映射方案：

```bash
cd deploy && sh install.sh -c plex -d /vol1/1000/docker/plex/zh-pack
```

脚本会把语言包放到宿主机目录，探测容器初始化系统后生成 compose 覆盖文件，并提示需要
添加的三条映射。原理是：`plex.mo` 路径固定，直接单文件映射；`zh.json` 位于
`Plug-ins-<哈希>` 目录、升级后会变，因此配合一个启动钩子，在每次容器启动时自动把
宿主机上的 `zh.json` 写进当前版本目录。

- 宿主机目录持久化，删容器不丢
- 启动钩子自动重应用，升级后不丢
- 钩子失败不阻断 Plex 启动
- 删除映射重建容器即可完全回滚官方文件

详细说明见 [`deploy/README.md`](deploy/README.md)。

## 注意事项
- 提供的文件地址仅供参考，因为安装设置差异，文件地址也许不会完全一致，请在类似的目录结构中查找文件。
- 通过 Docker 安装的 Plex Media Server 请在容器内部目录中查找和替换文件（非宿主机目录）。或者将对应的文件或目录映射到宿主机上，直接在宿主机上进行替换（见上方「Docker 映射部署」）。
- 建议在替换文件前先备份你原有的 `zh.json` 和 `plex.mo` 文件，以便你能够退回官方版本（如果有需要）。
- 语言包会持续更新，你可以关注本项目，及时获取最新版本，根据需要，某些翻译可能会在后续版本中变更。
- 更新 Plex 桌面客户端或 Plex Media Server 版本后会重置语言包，请在更新版本后重新替换语言包。

## 赞赏
如果你觉得这个项目对你有用，可以考虑请我喝杯咖啡或者给我一个⭐️。谢谢你的支持！

<img width="383" alt="赞赏" src="https://github.com/user-attachments/assets/bdd2226b-6282-439d-be92-5311b6e9d29c">
