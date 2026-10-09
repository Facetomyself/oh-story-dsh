### Phase 2：确定数据来源

**扫榜需要真实数据支撑。** 起点和番茄只跑本技能目录里的 `bridge/rankmin_cli.py`。它是匿名 HTTP，不带 Cookie，不进详情页，也不保存原始 HTML。七猫、晋江、刺猬猫本版本没有 provider。

| 优先级 | 模式 | 说明 | 何时用 |
|--------|------|------|--------|
| 1 | **rankmin** | 起点移动榜、番茄榜单页，写出榜单 markdown | 选了起点或番茄 |
| 2 | **用户提供** | 用户粘贴榜单截图/文字 | 用户已有数据，或平台没有 provider |
| 3 | **内置知识** | 基于知识库趋势数据做分析 | 命令失败且用户无数据时 |

#### 起点和番茄

1. 平台参考只读分析维度和字段：[起点](references/platform-qidian.md) / [番茄](references/platform-fanqie.md)。不要执行参考里的旧命令，不要启动 CDP。
2. 每次扫榜新建输出目录 `扫榜/{YYYYMMDD}/`（同日再扫加 `-2`）。在本技能目录执行：`python3 bridge/rankmin_cli.py --out {输出目录} --limit 20 --qidian yuepiao,hotsales,readindex`。番茄再加 `--fanqie male-hot-xifangqihuan,male-newbook-xifangqihuan,female-hot-gufengshiqing,female-newbook-gufengshiqing`。作者点名的榜或题材换成对应别名，不要一次扫完全部题材。
3. 成功时写出 `起点{榜}_{日期}.md` 和 `番茄{榜}_{日期}.md`。主会话读这些文件。本包没有聚合脚本，不要运行 `scripts/` 下的采集或聚合命令。
4. 退出码 2、缺模块或请求失败：该榜这次没拿到。不要编造名次，不要改走 CDP，也不要去作品页或章节页补标题。番茄若报私用区字段，报告里写明缺的是哪个字段。
5. 同方向不到 15 本标「少」，等同 `[数据稀疏]`。要看某一条的简介，直接打开对应 markdown，一次一个方向。

#### 七猫、晋江、刺猬猫

本版本没有 provider。不要启动 CDP，也不要把 [七猫](references/platform-qimao.md) / [晋江](references/platform-jjwxc.md) / [刺猬猫](references/platform-ciweimao.md) 里的旧命令改回去跑。作者没提供榜单时，结论不含这些平台。分析维度只作历史对照。

#### 其他数据来源

**用户提供：** 粘贴或截图整理成 `# {平台} · {榜单名}` 标题、每本一段 `### #{排名} {书名}` 加一行 `*作者 · 题材 · 连载中 · 120万字 · 3.5万收藏*`，存进本次输出目录。不要为了整理去抓站。

**内置知识：** 加载 `references/genre-trends.md`，明确标注「以下分析基于历史趋势数据；未完成实时榜单校验前只能作为候选假设。」并列出需要复扫的榜单。

