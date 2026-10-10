### Phase 2：确定数据来源

**扫榜需要真实数据支撑。** 起点、番茄和刺猬猫只跑本技能目录里的 `bridge/rankmin_cli.py`。起点男频是匿名 HTTP，不带 Cookie，不进详情页，也不保存原始 HTML。番茄走同目录的 `bridge/fanqie_app`，取分类热门和分类最新的明文。刺猬猫走同目录的 `bridge/ciweimao_app`，也就是 App 采集器的协议客户端。七猫、晋江本版本没有 provider。

| 优先级 | 模式 | 说明 | 何时用 |
|--------|------|------|--------|
| 1 | **rankmin** | 起点移动男频榜、番茄分类热门/最新、刺猬猫 App 排行，写出榜单 markdown | 选了起点、番茄或刺猬猫 |
| 2 | **用户提供** | 用户粘贴榜单截图/文字 | 用户已有数据，或平台没有 provider |
| 3 | **内置知识** | 基于知识库趋势数据做分析 | 命令失败且用户无数据时 |

#### 起点和番茄

1. 平台参考只读分析维度和字段：[起点](references/platform-qidian.md) / [番茄](references/platform-fanqie.md)。不要执行参考里的旧命令，不要启动 CDP。
2. 每次扫榜新建输出目录 `扫榜/{YYYYMMDD}/`（同日再扫加 `-2`）。在本技能目录执行：`python3 bridge/rankmin_cli.py --out {输出目录} --limit 20 --qidian yuepiao,hotsales,readindex`。番茄再加 `--fanqie male-hot-xifangqihuan,male-newbook-xifangqihuan,female-hot-gufengshiqing,female-newbook-gufengshiqing`。作者点名的榜或题材换成对应别名，不要一次扫完全部题材。
3. 成功时写出 `起点{榜}_{日期}.md` 和 `番茄{榜}_{日期}.md`。主会话读这些文件。本包没有聚合脚本，不要运行 `scripts/` 下的采集或聚合命令。
4. 退出码 2、缺模块或请求失败：该榜这次没拿到。不要编造名次，不要改走 CDP，也不要去作品页或章节页补标题。起点女生精选榜和女生月票榜当前没有公开列表，报 unavailable 时结论不含这两条。番茄 `hot` 是分类热门，`newbook` 是分类最新。
5. 同方向不到 15 本标「少」，等同 `[数据稀疏]`。要看某一条的简介，直接打开对应 markdown，一次一个方向。

#### 刺猬猫

1. 平台参考只读分析维度：[刺猬猫](references/platform-ciweimao.md)。不要执行参考里的旧命令，不要启动 CDP。
2. 同一条命令加 `--ciweimao fans_value:week,favor:week,tsukkomi:week,yp_new:month`。作者点名的榜换成 `order:time_type`，不要一次扫完全部。
3. 成功时写出 `刺猬猫{榜}_{日期}.md`。没有账号环境变量时，客户端按自己的游客注册取得会话，写在运行用户的 `~/.dsh/ciweimao-guest.json`。出口与采集器相同：`CIWEIMAO_PROXY_URL`，或 `KDL_SECRET_ID` / `KDL_SECRET_KEY`，密钥文件也可放在 `~/.dsh/ciweimao/`。不要读 `tokens.json`，不要把会话或代理地址写进报告，不要下章节。
4. 退出码 2：该榜这次没拿到。缺模块、注册失败或书名缺了哪个 `book_id`，报告里照命令原文写。榜单值写 `[待补]` 时不要改去作品页补。
5. 同方向不到 10 本标「少」。

#### 七猫、晋江

本版本没有 provider。不要启动 CDP，也不要把 [七猫](references/platform-qimao.md) / [晋江](references/platform-jjwxc.md) 里的旧命令改回去跑。作者没提供榜单时，结论不含这些平台。分析维度只作历史对照。

#### 其他数据来源

**用户提供：** 粘贴或截图整理成 `# {平台} · {榜单名}` 标题、每本一段 `### #{排名} {书名}` 加一行 `*作者 · 题材 · 连载中 · 120万字 · 3.5万收藏*`，存进本次输出目录。不要为了整理去抓站。

**内置知识：** 加载 `references/genre-trends.md`，明确标注「以下分析基于历史趋势数据；未完成实时榜单校验前只能作为候选假设。」并列出需要复扫的榜单。

