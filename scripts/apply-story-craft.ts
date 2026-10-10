import { copyFile, cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { ohStoryRoot, refreshBundledManifest } from "./knowledge-assets.js";

const overlayRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../overlays/story-craft");
const rankBridgeRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../overlays/rank-bridge");

const copies = [
  ["scene-grammar.md", "skills/story-long-write/references/scene-grammar.md"],
  ["check-scene-grammar.cjs", "skills/story-long-write/scripts/check-scene-grammar.cjs"],
  ["prose-surface.md", "skills/story-long-write/references/prose-surface.md"],
  ["check-prose-surface.cjs", "skills/story-long-write/scripts/check-prose-surface.cjs"]
] as const;

const removedAfterSync = [
  "skills/story-setup/references/agent-references/scene-grammar.md"
] as const;

interface Replacement {
  readonly path: string;
  readonly to: string;
  readonly from: readonly string[];
}

const replacements: readonly Replacement[] = [
  {
    path: "skills/story-long-write/SKILL.md",
    to: "2. 主会话直接写正文时，首次落笔前完整读取 `references/long-format.md` 与 `references/writing-craft.md`（和写手同一套技法；第 11 节是场面计数，不另读 scene-grammar.md；第 12 节是句子表面计数，不另读 prose-surface.md）；",
    from: [
      "2. 主会话直接写正文时，首次落笔前完整读取 `references/long-format.md` 与 `references/writing-craft.md`（和写手同一套技法；第 11 节是场面计数，不另读 scene-grammar.md）；",
      "2. 主会话直接写正文时，首次落笔前完整读取 `references/long-format.md`、`references/writing-craft.md` 与 `references/scene-grammar.md`（场面语法；和写手同一套技法）；",
      "2. 主会话直接写正文时，首次落笔前完整读取 `references/long-format.md` 与 `references/writing-craft.md`（和写手同一套技法）；"
    ]
  },
  {
    path: "roles/narrative-writer.md",
    to: "| `story-setup/references/agent-references/writing-craft.md` | **产出正文全程**（从细纲到正文、场景推进、疏密分配、物件三次出现、套式反应删除测试；第 11 节场面计数必须执行，不另读 scene-grammar.md；第 12 节句子表面计数必须执行，不另读 prose-surface.md） |",
    from: [
      "| `story-setup/references/agent-references/writing-craft.md` | **产出正文全程**（从细纲到正文、场景推进、疏密分配、物件三次出现、套式反应删除测试；第 11 节场面计数必须执行，不另读 scene-grammar.md） |",
      [
        "| `story-setup/references/agent-references/writing-craft.md` | **产出正文全程**（从细纲到正文、场景推进、疏密分配、物件三次出现、套式反应删除测试；第 11 节场面语法必须执行） |",
        "| `story-setup/references/agent-references/scene-grammar.md` | **产出正文全程**。与 writing-craft.md 第 11 节是同一份规则。若 oh_story_bundled_reference 的可选列表里还没有该路径，以第 11 节为准，视为已读，继续写，不要停笔 |"
      ].join("\n"),
      "| `story-setup/references/agent-references/writing-craft.md` | **产出正文全程**（从细纲到正文、场景推进、疏密分配、物件三次出现、套式反应删除测试） |"
    ]
  },
  {
    path: "skills/story-long-write/references/workflow-chapter.md",
    to: "   - **意图确认**：一句话写清本章意图（例：「快节奏打脸——账单暴露→逼问→反证→公开代价」）。对照：细纲是唯一剧情蓝图，新增物按「新增物三级」；底牌不因章尾钩子提前泄露；细纲重复的同一要求只兑现一次；爽点前有可指认的铺垫，打脸/揭露章写在场配角的差异反应。场面以细纲计数表为准：有「危机层」就按表里的阻碍数和展示对象写，不改数、不另加阻碍。没有这块或全是 `[待补充]`，不扩纲。",
    from: [
      "   - **意图确认**：一句话写清本章意图（例：「快节奏打脸——账单暴露→逼问→反证→公开代价」）。对照：细纲是唯一剧情蓝图，新增物按「新增物三级」；底牌不因章尾钩子提前泄露；细纲重复的同一要求只兑现一次；爽点前有可指认的铺垫，打脸/揭露章写在场配角的差异反应。再按 [scene-grammar.md](scene-grammar.md) 核对这场戏：危机落在哪一层需求，行动有没有阻碍或转折，展示打在谁的旧认知上，章尾新坑是什么。细纲可选块写了「场面」就照它，没写就在意图里补这四句，不为此扩纲。",
      "   - **意图确认**：一句话写清本章意图（例：「快节奏打脸——账单暴露→逼问→反证→公开代价」）。对照：细纲是唯一剧情蓝图，新增物按「新增物三级」；底牌不因章尾钩子提前泄露；细纲重复的同一要求只兑现一次；爽点前有可指认的铺垫，打脸/揭露章写在场配角的差异反应。"
    ]
  },
  {
    path: "skills/story-long-write/references/workflow-chapter.md",
    to: "9. **检查钩子、爽点与契约**：章尾有往下看的理由（低压/过场章留阶段目标即可）；高压/推进章爽点到位；对着成稿过契约四问——主角是否靠自己的选择挣到本章结果？收益是否被配角、机构或巧合无交换地拿走？有没有提前动用后面的底牌？旧期待付利息、留新期待了吗？任一问不过就按问改：没挣到→让结果落在他的选择或判断上；收益被拿走→补交换或让他拿回控制点；提前用了底牌→换成本卷已解锁的手段；没付利息→给旧期待一个小兑现再留新钩。然后跑 `node scripts/check-scene-grammar.cjs --json --prose {本章正文路径}`：exit 1 只改 `repair_scope` 点名的集体反应句和章尾感悟，改成某个在场者的动作或台词；不新增情节，也不为了凑阻碍数另写一次拦阻。细纲里的阻碍数是几，正文就写表里那几次。低压且阻碍数为 0 时不补阻碍。再跑 `node scripts/check-prose-surface.cjs --json --prose {本章正文路径}`：exit 1 只改 `repair_scope` 点名的套语、引号外的「你」和不足 11 个汉字的动作段。套语换成这句里已有的动作或物件，不换成另一个套语。引号内的「你」和「我」不动。文风写明第二人称时给检查器加 `--allow-ni`。不新增情节，最多两轮。不达标只修批准内容，修后重跑步骤 8；需补强、契约破坏都在本章汇报里告诉作者。",
    from: [
      "9. **检查钩子、爽点与契约**：章尾有往下看的理由（低压/过场章留阶段目标即可）；高压/推进章爽点到位；对着成稿过契约四问——主角是否靠自己的选择挣到本章结果？收益是否被配角、机构或巧合无交换地拿走？有没有提前动用后面的底牌？旧期待付利息、留新期待了吗？任一问不过就按问改：没挣到→让结果落在他的选择或判断上；收益被拿走→补交换或让他拿回控制点；提前用了底牌→换成本卷已解锁的手段；没付利息→给旧期待一个小兑现再留新钩。然后跑 `node scripts/check-scene-grammar.cjs --json --prose {本章正文路径}`：exit 1 只改 `repair_scope` 点名的集体反应句和章尾感悟，改成某个在场者的动作或台词；不新增情节，也不为了凑阻碍数另写一次拦阻。细纲里的阻碍数是几，正文就写表里那几次。低压且阻碍数为 0 时不补阻碍。不达标只修批准内容，修后重跑步骤 8；需补强、契约破坏都在本章汇报里告诉作者。",
      "9. **检查钩子、爽点与契约**：章尾有往下看的理由（低压/过场章留阶段目标即可）；高压/推进章爽点到位；对着成稿过契约四问——主角是否靠自己的选择挣到本章结果？收益是否被配角、机构或巧合无交换地拿走？有没有提前动用后面的底牌？旧期待付利息、留新期待了吗？再过场面四问：危机有没有落到具体的那一层需求上，而不只是被命名；行动里有没有阻碍或转折；展示有没有打在某个在场者的旧认知上；章尾有没有新坑。任一问不过就按问改：没挣到→让结果落在他的选择或判断上；收益被拿走→补交换或让他拿回控制点；提前用了底牌→换成本卷已解锁的手段；没付利息→给旧期待一个小兑现再留新钩；危机只是标签→写成那一层需求被伤到的事实；没有阻碍→在得手前补上已批准范围内的阻力；没有旧认知→补这个在场者事先的一句判断；没有新坑→停在下一个麻烦上，不另起感悟。不达标只修批准内容，修后重跑步骤 8；需补强、契约破坏都在本章汇报里告诉作者。",
      "9. **检查钩子、爽点与契约**：章尾有往下看的理由（低压/过场章留阶段目标即可）；高压/推进章爽点到位；对着成稿过契约四问——主角是否靠自己的选择挣到本章结果？收益是否被配角、机构或巧合无交换地拿走？有没有提前动用后面的底牌？旧期待付利息、留新期待了吗？任一问不过就按问改：没挣到→让结果落在他的选择或判断上；收益被拿走→补交换或让他拿回控制点；提前用了底牌→换成本卷已解锁的手段；没付利息→给旧期待一个小兑现再留新钩。不达标只修批准内容，修后重跑步骤 8；需补强、契约破坏都在本章汇报里告诉作者。"
    ]
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    to: "语义仍不设 checker。场面计数另跑 `check-scene-grammar.cjs`，见下方落盘段。",
    from: ["语义仍不设 checker。"]
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    to: "本检查只在新建/补建/回填时执行；既有项目的旧细纲不因此阻断写正文。场面块另跑 `node scripts/check-scene-grammar.cjs --json --project {书目录} --chapter {N}`：没有场面块或十二字段全是 `[待补充]` 时 exit 0。exit 1 只改 `repair_scope` 点名的场面字段，最多两轮。exit 2 如实报告。旧细纲没有场面块，不阻断写正文。",
    from: ["本检查只在新建/补建/回填时执行；既有项目的旧细纲不因此阻断写正文。"]
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    to: `- 契约风险：只在本章让单元卡「契约风险」变化时写
- 场面（新写或补建时可填；不填或整表 \`[待补充]\` 都通过。写了实词就必须十二字段齐全，由 check-scene-grammar.cjs 计数，不新增必填字段）：
  - 压力：{高压 / 推进 / 低压 / 修炼 / 过场 / 关系 / 信息}
  - 危机层：{生理 / 安全 / 归属 / 尊重 / 自我实现}
  - 危机事实：{至少 8 个汉字，不能只写层名}
  - 短线目标：{一个，至少 4 个汉字，不要分号}
  - 阻碍数：{高压或推进写 1 或 2；低压类写 0 或 1}
  - 阻碍：{阻碍数 ≥ 1 时写那一次，至少 8 个汉字；为 0 时写「无」}
  - 收获类：{身份 / 资源 / 能力 / 尊重 / 认同；低压类可以写「无」}
  - 收获物：{一件可见物，至少 4 个汉字；收获类为无时写「无」}
  - 展示对象：{一个在场者；低压类可以写「无」}
  - 旧认知：{此人得手前的一句台词或动作，至少 8 个汉字；展示对象为无时写「无」}
  - 展示落点：{改口 / 收手 / 不肯认 / 换评价；展示对象为无时写「无」}
  - 章尾新坑：{至少 8 个汉字；低压类写成「阶段：…」}
\`\`\``,
    from: [
      `- 契约风险：只在本章让单元卡「契约风险」变化时写
- 场面（新写或补建时尽量填；未知写 \`[待补充]\`，不因此判失败，也不新增必填字段）：
  - 危机：{伤到谁的哪一层需求：生理 / 安全 / 归属 / 尊重 / 自我实现}
  - 收获：{这一场拿到的身份、资源、能力、尊重或认同；行动里的阻碍或转折}
  - 展示：{向谁亮；对方原认知；被打掉的那一个认知}
  - 章尾新坑：{本场结束后的下一个危机；没有就写「无，功能是…」}
\`\`\``,
      "- 契约风险：只在本章让单元卡「契约风险」变化时写\n```"
    ]
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    to: "字段不完整时先补齐；无法从材料确定的关系或副线写 `[待补充]`，不得杜撰。新写或补建的细纲可以在可选块填场面计数表；不填或整表 `[待补充]` 时 `check-scene-grammar.cjs` 通过。写了实词就必须过该检查，exit 1 只改点名的场面字段。",
    from: [
      "字段不完整时先补齐；无法从材料确定的关系或副线写 `[待补充]`，不得杜撰。新写或补建的细纲，材料够时在可选块写下场面四行；不够就写 `[待补充]`，检查器不因此失败。",
      "字段不完整时先补齐；无法从材料确定的关系或副线写 `[待补充]`，不得杜撰。"
    ]
  },
  {
    path: "skills/story-long-scan/SKILL.md",
    to: "以本次输出目录里的榜单 markdown 为主，按所选平台参考里的「分析维度」看，再提取通用维度：",
    from: ["以聚合结果为主，按所选平台参考里的「分析维度」看，再提取通用维度："]
  },
  {
    path: "skills/story-long-scan/SKILL.md",
    to: "2. **新题材信号**：新书榜列、多榜重合；`扫榜/` 下上一次的日期目录里有榜单 markdown 就对比",
    from: ["2. **新题材信号**：新书榜列、多榜重合；`扫榜/` 下上一次的日期目录里有 `扫榜聚合.md` 就对比"]
  },
  {
    path: "skills/story-long-scan/SKILL.md",
    to: "**从文件接上：** 先读 `{outdir}/选题决策.md` 的「扫榜结论」和本次榜单 markdown，不靠对话记忆；两者都没有就回 Phase 2。",
    from: ["**从文件接上：** 先读 `{outdir}/选题决策.md` 的「扫榜结论」和 `扫榜聚合.md`，不靠对话记忆；两者都没有就回 Phase 2。"]
  },
  {
    path: "skills/story-long-scan/SKILL.md",
    to: `| 五份平台参考（链接见 Phase 2） | 起点、番茄、刺猬猫读「分析维度」和字段；七猫、晋江本版本没有 provider，不执行其中的采集命令 |
| [bridge/rankmin_cli.py](bridge/rankmin_cli.py) | 起点移动榜、番茄榜单页、刺猬猫 App 排行。\`--self-test\` 不联网。失败退出码 2，不编造榜单 |`,
    from: [`| 五份平台参考（链接见 Phase 2） | 起点、番茄读「分析维度」和字段；七猫、晋江、刺猬猫本版本没有 provider，不执行其中的采集命令 |
| [bridge/rankmin_cli.py](bridge/rankmin_cli.py) | 起点移动榜和番茄榜单页。\`--self-test\` 不联网。失败退出码 2，不编造榜单 |`,
      `| 五份平台参考（链接见「脚本采集模式」第 1 步） | 「确定数据来源」：只读所选平台那份——榜单网址、命令、字段、故障排查、平台分析维度 |
| [scripts/aggregate-rank.js](scripts/aggregate-rank.js) | 把输出目录里的原始榜单聚合成短表（\`--out\` 落盘，\`--sample\` 抽原始条目，\`--json\` 机读），主会话只读它 |
| [scripts/cdp-utils.js](scripts/cdp-utils.js) | CDP 公共工具函数（ab/sleep/evalJSON/safeStr/scrollLoad/getArg），各采集脚本共用 |
| [scripts/fanqie-rank-scraper.js](scripts/fanqie-rank-scraper.js) | 番茄榜单采集，用法见番茄参考 |
| [scripts/qidian-rank-scraper.js](scripts/qidian-rank-scraper.js) | 起点榜单采集，用法见起点参考 |
| [scripts/qimao-rank-scraper.js](scripts/qimao-rank-scraper.js) | 七猫榜单采集，用法见七猫参考 |
| [scripts/jjwxc-rank-scraper.js](scripts/jjwxc-rank-scraper.js) | 晋江榜单采集，用法见晋江参考 |
| [scripts/ciweimao-rank-scraper.js](scripts/ciweimao-rank-scraper.js) | 刺猬猫榜单采集，用法见刺猬猫参考 |`]
  },
  {
    path: "skills/story-long-scan/references/platform-qidian.md",
    to: "作者选了起点才读本文。采集只走本技能 `bridge/rankmin_cli.py` 的起点移动榜。不要执行下文旧命令，不要回退 CDP，不要进详情页。",
    from: ["作者选了起点才读本文。默认不需要 Chrome：脚本先读 `https://m.qidian.com` 移动端 SSR pageContext，移动端不可用时才回退 CDP/PC 页面，文件头 `抓取方式` 标 `mobile-ssr` 或 `cdp-pc`。"]
  },
  {
    path: "skills/story-long-scan/references/platform-qidian.md",
    to: "在技能目录执行 `python3 bridge/rankmin_cli.py --out {输出目录} --limit 20 --qidian {榜单别名}`。别名用下表的 `--type` 列。不要全采，不要进详情页，不要 CDP。",
    from: ["`node scripts/qidian-rank-scraper.js --type {榜单} --outdir {输出目录}`（`--type all` 全采；`--mode mobile|cdp` 强制一种方式；`--detail yes` 进详情页补标签、简介、最新更新）"]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "作者选了番茄才读本文。采集走本技能 `bridge/fanqie_app` 的 App 分类榜，经 `bridge/rankmin_cli.py` 写榜。`hot` 是分类热门，`newbook` 是分类最新。不要启动 CDP，不要下章节，不要进网页榜补标题。",
    from: [
      "作者选了番茄才读本文。采集只走本技能 `bridge/rankmin_cli.py` 的榜单页。书名若仍是私用区字符，命令失败并指出缺的字段。不要启动 CDP，不要进详情页或章节页补标题。",
      "作者选了番茄才读本文。番茄列表页有字体反爬，须先用 `/browser-cdp` 启动 Chrome，再由脚本从详情页（内嵌 JSON `bookName`/`author`/`abstract`/`categoryV2` + `<title>` + og:meta）多策略解码书名、作者、题材、标签、简介。"
    ]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "```bash\npython3 bridge/rankmin_cli.py --out {输出目录} --limit 20 --fanqie male-hot-xifangqihuan,female-hot-gufengshiqing\n```\n\n别名示例：`male-hot-xifangqihuan`、`female-newbook-gufengshiqing`、`1_2_1141`。不要一次扫完全部题材。",
    from: ["```bash\nnode scripts/fanqie-rank-scraper.js --channel 1 --type 2 --outdir {输出目录}     # 男频阅读榜（默认）\nnode scripts/fanqie-rank-scraper.js --channel all --top 15 --outdir {输出目录}   # 男女频，每题材前 15 本\n```"]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "书库「最热」不在本版本的 provider 里。不要抓 library 页，也不要进详情页补标题。",
    from: ["```bash\nnode scripts/fanqie-rank-scraper.js --source library --channel all --outdir {输出目录}            # 男、女各一份：连载中、30 万字以下、前 3 页\nnode scripts/fanqie-rank-scraper.js --source library --channel mix --pages 5 --outdir {输出目录}  # 不分男女\n```"]
  },
  {
    path: "skills/story-long-scan/references/platform-qimao.md",
    to: "作者选了七猫才读本文。本版本没有七猫 provider。不要启动 CDP，也不要把下文命令改回采集脚本。作者没有提供榜单时，结论不含七猫。分析维度只作历史对照。",
    from: ["作者选了七猫才读本文。需先用 `/browser-cdp` 启动 Chrome；页面无明显反爬，脚本滚动加载，男生榜/女生榜 tab 切换（失败重试）。"]
  },
  {
    path: "skills/story-long-scan/references/platform-jjwxc.md",
    to: "作者选了晋江才读本文。本版本没有晋江 provider。不要启动 CDP，也不要把下文命令改回采集脚本。作者没有提供榜单时，结论不含晋江。分析维度只作历史对照。",
    from: ["作者选了晋江才读本文。需先用 `/browser-cdp` 启动 Chrome。脚本两步走：① 列表页 `topten.php` 取频道分组与书名/作者，从书名链接取 `novelid`（排除「X 向《书名》投了 Y」霸王票记录）；② 进 `onebook.php?novelid=` 详情页补采核心指标。晋江是 gb18030 编码，脚本已按此解码；详情指标公开，无需登录。"]
  },
  {
    path: "skills/story-long-scan/references/platform-ciweimao.md",
    to: "作者选了刺猬猫才读本文。采集走本技能 `bridge/ciweimao_app` 的 App 协议客户端，经 `bridge/rankmin_cli.py` 写榜。不要启动 CDP，不要下章节。没有账号环境变量时客户端自己注册游客。出口用 `CIWEIMAO_PROXY_URL`，或 `~/.dsh/ciweimao/` 里的快代理密钥。",
    from: [
      "作者选了刺猬猫才读本文。采集只走本技能 `bridge/rankmin_cli.py` 的 App 排行。不要启动 CDP，不要注册游客，不要下章节。缺账号、login_token 或 device_token 时命令失败并指出缺的环境变量。",
      "作者选了刺猬猫才读本文。本版本没有刺猬猫 provider。不要启动 CDP，也不要把下文命令改回采集脚本。作者没有提供榜单时，结论不含刺猬猫。分析维度只作历史对照。",
      "作者选了刺猬猫才读本文。需先用 `/browser-cdp` 启动 Chrome。rank-index 单页展示全部榜单，脚本按文本解析，按书名归一回填作品页链接，带连通性自检与空结果重试。"
    ]
  },
  {
    path: "skills/story-long-scan/references/platform-qimao.md",
    to: "本版本不执行采集命令。入口 qimao.com/paihang 只说明榜单曾经在哪。",
    from: ["```bash\nnode scripts/qimao-rank-scraper.js --channel male --type hot --period day --outdir {输出目录}   # 男生大热榜日榜\nnode scripts/qimao-rank-scraper.js --channel all --type all --outdir {输出目录}                 # 全部\n```"]
  },
  {
    path: "skills/story-long-scan/references/platform-jjwxc.md",
    to: "本版本不执行采集命令。上面的 URL 只说明榜单曾经在哪。",
    from: ["```bash\nnode scripts/jjwxc-rank-scraper.js --type 12 --outdir {输出目录}        # 列表+详情（默认每频道前 10，详情上限 100）\nnode scripts/jjwxc-rank-scraper.js --type 12 --top 15 --detail-limit 60  # 调整每频道本数/详情总量\nnode scripts/jjwxc-rank-scraper.js --type 12 --list-only                 # 只采列表（快，无核心指标）\n```"]
  },
  {
    path: "skills/story-long-scan/references/platform-ciweimao.md",
    to: "排名、书名、作者、字数、作品页。题材和榜单值只有接口带了才写，没有就标 [待补]，不要下章节补。刺猬猫是小平台：同方向不到 10 本才算稀疏。",
    from: ["排名、书名、作者（仅榜首条目带）、题材（其余条目带）、榜单值（聚合的热度口径；各榜含义不同，不跨榜比较）、作品页链接。刺猬猫是小平台：同方向不到 10 本才算稀疏，聚合时加 `--sparse 10`。"]
  },
  {
    path: "skills/story-long-scan/references/platform-ciweimao.md",
    to: "在技能目录执行 `python3 bridge/rankmin_cli.py --out {输出目录} --limit 20 --ciweimao fans_value:week,favor:week,tsukkomi:week,yp_new:month`。别名是 `order:time_type`，例如 `favor:week`、`yp:month`。不要全采，不要读 tokens.json，不要下章节。",
    from: [
      "本版本不执行采集命令。click / favor / recommend / subscribe / monthly / tsukkomi / newbook / blade 只说明榜曾经怎么分。",
      "`node scripts/ciweimao-rank-scraper.js --type {榜单} --outdir {输出目录}`：click 点击榜 / favor 收藏榜 / recommend 推荐榜 / subscribe 订阅榜 / monthly 月票榜 / tsukkomi 吐槽榜 / newbook 新书榜 / blade 刀片榜 / all 全部（默认）。"
    ]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "不要逐题材扫完全部，也不要进详情页。文件名是 `番茄{榜}_{YYYYMMDD}.md`。",
    from: ["脚本逐题材采集（每题材上限约 20，`--top N` 可调），每 5 本一批请求详情页。默认组合：男频阅读榜全题材 + 女频阅读榜全题材；要看新风向再加新书榜（`--type 1`）或下面的书库「最热」。文件名 `番茄{频道}{榜单}_全题材_{YYYYMMDD}.md`。一份全题材就是七百来条，只读聚合结果，不整份读原始文件。"]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "书库筛选不在本版本里。缺标题就停，不要按页面顺序补 bookId，也不要进详情页解码。",
    from: ["`--stat 1|0|any`、`--count 0-4|any` 改筛选。默认组合（连载中、30 万字以下）是**正在起量的新书**：阅读榜被老书占住时，看它才知道新书里什么题材在冒头，文件名与列表名带「新书」，聚合时算进「新书榜」列。列表页书名和数字都被字体反爬，脚本只按页面顺序取 bookId，书名、题材、在读、字数都由详情页解码。"]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "命令退出码 2 时这次榜单作废。不要打开作品页，不要启动 Chrome，也不要下章节。",
    from: [
      "命令退出码 2 且指出私用区字段时，这次榜单作废。不要打开作品页，不要启动 Chrome，也不要重采详情。",
      "文件头 `数据质量` 标 `[标题解析异常]`（书名多为 `（标题待解析）`）：多为详情页结构变动或被登录/验证页拦截。在已登录的 Chrome 里手动打开任一 `https://fanqienovel.com/page/{bookId}`，确认页面正常、不是验证页；控制台报 `CDP 无响应` 就按 browser-cdp 重新启动 Chrome。确认正常后重采。"
    ]
  },
  {
    path: "skills/story-long-scan/references/platform-jjwxc.md",
    to: "作者自己提供的晋江样本如果没有收藏、营养液或积分、字数，标成数据不够，不要为此去抓详情页。",
    from: ["必须有详情页核心指标（收藏、营养液或积分、字数）：用了 `--list-only` 或文件头标 `[仅列表-无核心指标]` 的数据撑不起下面的分析，视为不合格，要重采。"]
  },
  {
    path: "skills/story-long-scan/references/platform-fanqie.md",
    to: "书名解不开时命令不会写出这份榜，不要把占位标题当成样本。",
    from: ["解码失败的书名显示 `（标题待解析）`，bookId 与链接保留供回查。"]
  },
  {
    path: "skills/story-short-scan/SKILL.md",
    to: "**核心信念：短篇市场变化快，题材信号有效期短。** 扫榜报告必须标注样本日期、趋势可信度和下次重新扫榜的时间。长篇起点、番茄和刺猬猫不在这里采集，走 story-long-scan 的 `bridge/rankmin_cli.py`。",
    from: [
      "**核心信念：短篇市场变化快，题材信号有效期短。** 扫榜报告必须标注样本日期、趋势可信度和下次重新扫榜的时间。长篇起点和番茄不在这里采集，走 story-long-scan 的 `bridge/rankmin_cli.py`。",
      "**核心信念：短篇市场变化快，题材信号有效期短。** 扫榜报告必须标注样本日期、趋势可信度和下次重新扫榜的时间。"
    ]
  }
];

async function replaceOnce(entry: Replacement): Promise<void> {
  const target = join(ohStoryRoot, entry.path);
  const text = await readFile(target, "utf8");
  if (text.includes(entry.to)) return;
  const hit = entry.from.find((candidate) => text.includes(candidate));
  if (hit === undefined) {
    throw new Error(`Story craft anchor missing in ${entry.path}`);
  }
  const next = text.replace(hit, entry.to);
  if (next === text) throw new Error(`Story craft replacement did not change ${entry.path}`);
  await writeFile(target, next);
}

async function section11Body(): Promise<string> {
  const source = await readFile(join(overlayRoot, "scene-grammar.md"), "utf8");
  const withoutTitle = source.replace(/^# .+\r?\n+/, "");
  const demoted = withoutTitle.replace(/^## /gm, "### ");
  const intro = [
    "## 11. 场面语法",
    "",
    "产出正文时执行下面的计数。写手只读本节，不另读 scene-grammar.md。细纲事实、本书文风和作者本轮明确约束优先。第 8 节深度限知、第 10 节在场者的账仍然有效。",
    ""
  ].join("\n");
  const body = demoted.endsWith("\n") ? demoted : `${demoted}\n`;
  return `${intro}\n${body}`;
}

async function section12Body(): Promise<string> {
  const source = await readFile(join(overlayRoot, "prose-surface.md"), "utf8");
  const withoutTitle = source.replace(/^# .+\r?\n+/, "");
  const demoted = withoutTitle.replace(/^## /gm, "### ");
  const intro = [
    "## 12. 句子表面",
    "",
    "只在写长篇正文时执行。拆书、扫榜、导入不读本节，也不跑下面的检查。写手只读本节，不另读 prose-surface.md。本书文风和作者本轮明确约束优先。",
    ""
  ].join("\n");
  const body = demoted.endsWith("\n") ? demoted : `${demoted}\n`;
  return `${intro}\n${body}`;
}

async function syncCraftSections(): Promise<void> {
  const target = join(ohStoryRoot, "skills/story-setup/references/agent-references/writing-craft.md");
  const text = await readFile(target, "utf8");
  const section = `${await section11Body()}${await section12Body()}`;
  const marker = "## 11. 场面语法";
  const index = text.indexOf(marker);
  const next = index === -1
    ? `${text.endsWith("\n") ? text : `${text}\n`}\n${section}`
    : `${text.slice(0, index)}${section}`;
  if (next !== text) await writeFile(target, next);
}

async function copyRankBridge(): Promise<void> {
  const packageTarget = join(ohStoryRoot, "skills/story-long-scan/bridge/rankmin");
  const cliTarget = join(ohStoryRoot, "skills/story-long-scan/bridge/rankmin_cli.py");
  await rm(packageTarget, { recursive: true, force: true });
  await mkdir(dirname(cliTarget), { recursive: true });
  await cp(join(rankBridgeRoot, "rankmin"), packageTarget, { recursive: true });
  await copyFile(join(rankBridgeRoot, "rankmin_cli.py"), cliTarget);
  const clientTarget = join(ohStoryRoot, "skills/story-long-scan/bridge/ciweimao_app");
  await rm(clientTarget, { recursive: true, force: true });
  await cp(join(rankBridgeRoot, "ciweimao_app"), clientTarget, { recursive: true });
  const fanqieTarget = join(ohStoryRoot, "skills/story-long-scan/bridge/fanqie_app");
  await rm(fanqieTarget, { recursive: true, force: true });
  await cp(join(rankBridgeRoot, "fanqie_app"), fanqieTarget, { recursive: true });
}

async function spliceLongScanPhase2(): Promise<void> {
  const body = await readFile(join(rankBridgeRoot, "long-scan-phase2.md"), "utf8");
  const normalized = body.endsWith("\n") ? body : `${body}\n`;
  const target = join(ohStoryRoot, "skills/story-long-scan/SKILL.md");
  const text = await readFile(target, "utf8");
  const start = "### Phase 2：确定数据来源";
  const end = "### Phase 3：数据分析";
  const startAt = text.indexOf(start);
  const endAt = text.indexOf(end);
  if (startAt < 0 || endAt < 0 || endAt <= startAt) {
    throw new Error("story-long-scan Phase 2 anchors missing");
  }
  const next = `${text.slice(0, startAt)}${normalized}\n${text.slice(endAt)}`;
  if (next !== text) await writeFile(target, next);
}

export async function applyStoryCraft(): Promise<void> {
  for (const relativePath of removedAfterSync) {
    await rm(join(ohStoryRoot, relativePath), { force: true });
  }
  for (const [sourceName, relativePath] of copies) {
    const target = join(ohStoryRoot, relativePath);
    await mkdir(dirname(target), { recursive: true });
    await copyFile(join(overlayRoot, sourceName), target);
  }
  await copyRankBridge();
  for (const entry of replacements) await replaceOnce(entry);
  await spliceLongScanPhase2();
  await syncCraftSections();
}

const invokedDirectly = process.argv[1] !== undefined
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

if (invokedDirectly) {
  await applyStoryCraft();
  const manifest = await refreshBundledManifest();
  process.stdout.write(`Applied story craft. Manifest tracks ${String(manifest.files.length)} files.\n`);
}
