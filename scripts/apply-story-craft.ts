import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { ohStoryRoot, refreshBundledManifest } from "./knowledge-assets.js";

const overlayRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../overlays/story-craft");

const copies = [
  ["scene-grammar.md", "skills/story-long-write/references/scene-grammar.md"],
  ["scene-grammar.md", "skills/story-setup/references/agent-references/scene-grammar.md"]
] as const;

interface Replacement {
  readonly path: string;
  readonly marker: string;
  readonly from: string;
  readonly to: string;
}

const replacements: readonly Replacement[] = [
  {
    path: "skills/story-long-write/SKILL.md",
    marker: "references/scene-grammar.md",
    from: "2. 主会话直接写正文时，首次落笔前完整读取 `references/long-format.md` 与 `references/writing-craft.md`（和写手同一套技法）；",
    to: "2. 主会话直接写正文时，首次落笔前完整读取 `references/long-format.md`、`references/writing-craft.md` 与 `references/scene-grammar.md`（场面语法；和写手同一套技法）；"
  },
  {
    path: "roles/narrative-writer.md",
    marker: "agent-references/scene-grammar.md",
    from: "| `story-setup/references/agent-references/writing-craft.md` | **产出正文全程**（从细纲到正文、场景推进、疏密分配、物件三次出现、套式反应删除测试） |",
    to: [
      "| `story-setup/references/agent-references/writing-craft.md` | **产出正文全程**（从细纲到正文、场景推进、疏密分配、物件三次出现、套式反应删除测试；第 11 节场面语法必须执行） |",
      "| `story-setup/references/agent-references/scene-grammar.md` | **产出正文全程**。与 writing-craft.md 第 11 节是同一份规则。若 oh_story_bundled_reference 的可选列表里还没有该路径，以第 11 节为准，视为已读，继续写，不要停笔 |"
    ].join("\n")
  },
  {
    path: "skills/story-long-write/references/workflow-chapter.md",
    marker: "再按 [scene-grammar.md](scene-grammar.md) 核对这场戏",
    from: "   - **意图确认**：一句话写清本章意图（例：「快节奏打脸——账单暴露→逼问→反证→公开代价」）。对照：细纲是唯一剧情蓝图，新增物按「新增物三级」；底牌不因章尾钩子提前泄露；细纲重复的同一要求只兑现一次；爽点前有可指认的铺垫，打脸/揭露章写在场配角的差异反应。",
    to: "   - **意图确认**：一句话写清本章意图（例：「快节奏打脸——账单暴露→逼问→反证→公开代价」）。对照：细纲是唯一剧情蓝图，新增物按「新增物三级」；底牌不因章尾钩子提前泄露；细纲重复的同一要求只兑现一次；爽点前有可指认的铺垫，打脸/揭露章写在场配角的差异反应。再按 [scene-grammar.md](scene-grammar.md) 核对这场戏：危机落在哪一层需求，行动有没有阻碍或转折，展示打在谁的旧认知上，章尾新坑是什么。细纲可选块写了「场面」就照它，没写就在意图里补这四句，不为此扩纲。"
  },
  {
    path: "skills/story-long-write/references/workflow-chapter.md",
    marker: "再过场面四问",
    from: "9. **检查钩子、爽点与契约**：章尾有往下看的理由（低压/过场章留阶段目标即可）；高压/推进章爽点到位；对着成稿过契约四问——主角是否靠自己的选择挣到本章结果？收益是否被配角、机构或巧合无交换地拿走？有没有提前动用后面的底牌？旧期待付利息、留新期待了吗？任一问不过就按问改：没挣到→让结果落在他的选择或判断上；收益被拿走→补交换或让他拿回控制点；提前用了底牌→换成本卷已解锁的手段；没付利息→给旧期待一个小兑现再留新钩。不达标只修批准内容，修后重跑步骤 8；需补强、契约破坏都在本章汇报里告诉作者。",
    to: "9. **检查钩子、爽点与契约**：章尾有往下看的理由（低压/过场章留阶段目标即可）；高压/推进章爽点到位；对着成稿过契约四问——主角是否靠自己的选择挣到本章结果？收益是否被配角、机构或巧合无交换地拿走？有没有提前动用后面的底牌？旧期待付利息、留新期待了吗？再过场面四问：危机有没有落到具体的那一层需求上，而不只是被命名；行动里有没有阻碍或转折；展示有没有打在某个在场者的旧认知上；章尾有没有新坑。任一问不过就按问改：没挣到→让结果落在他的选择或判断上；收益被拿走→补交换或让他拿回控制点；提前用了底牌→换成本卷已解锁的手段；没付利息→给旧期待一个小兑现再留新钩；危机只是标签→写成那一层需求被伤到的事实；没有阻碍→在得手前补上已批准范围内的阻力；没有旧认知→补这个在场者事先的一句判断；没有新坑→停在下一个麻烦上，不另起感悟。不达标只修批准内容，修后重跑步骤 8；需补强、契约破坏都在本章汇报里告诉作者。"
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    marker: "结构公式、场面等在末尾",
    from: "细纲是正文写作的章节蓝图，而不是只列事件和钩子的清单。模板见下（唯一权威副本：九个必填字段、四个小节、不含逐点字数的四列情节点表，阶段位置、结构公式等在末尾「可选」块）。新建、补建、回填都按权威模板补齐，未知字段写 `[待补充]`，不为补齐字段杜撰副线或人物关系。",
    to: "细纲是正文写作的章节蓝图，而不是只列事件和钩子的清单。模板见下（唯一权威副本：九个必填字段、四个小节、不含逐点字数的四列情节点表，阶段位置、结构公式、场面等在末尾「可选」块）。新建、补建、回填都按权威模板补齐，未知字段写 `[待补充]`，不为补齐字段杜撰副线或人物关系。"
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    marker: "场面（新写或补建时尽量填",
    from: "- 契约风险：只在本章让单元卡「契约风险」变化时写\n```",
    to: `- 契约风险：只在本章让单元卡「契约风险」变化时写
- 场面（新写或补建时尽量填；未知写 \`[待补充]\`，不因此判失败，也不新增必填字段）：
  - 危机：{伤到谁的哪一层需求：生理 / 安全 / 归属 / 尊重 / 自我实现}
  - 收获：{这一场拿到的身份、资源、能力、尊重或认同；行动里的阻碍或转折}
  - 展示：{向谁亮；对方原认知；被打掉的那一个认知}
  - 章尾新坑：{本场结束后的下一个危机；没有就写「无，功能是…」}
\`\`\``
  },
  {
    path: "skills/story-long-write/references/workflow-outline.md",
    marker: "新写或补建的细纲，材料够时在可选块写下场面四行",
    from: "字段不完整时先补齐；无法从材料确定的关系或副线写 `[待补充]`，不得杜撰。",
    to: "字段不完整时先补齐；无法从材料确定的关系或副线写 `[待补充]`，不得杜撰。新写或补建的细纲，材料够时在可选块写下场面四行；不够就写 `[待补充]`，检查器不因此失败。"
  }
];

async function replaceOnce(entry: Replacement): Promise<void> {
  const target = join(ohStoryRoot, entry.path);
  const text = await readFile(target, "utf8");
  if (text.includes(entry.marker)) return;
  if (!text.includes(entry.from)) {
    throw new Error(`Story craft anchor missing in ${entry.path}: ${entry.marker}`);
  }
  const next = text.replace(entry.from, entry.to);
  if (next === text) throw new Error(`Story craft replacement did not change ${entry.path}`);
  await writeFile(target, next);
}

async function appendSection11(): Promise<void> {
  const target = join(ohStoryRoot, "skills/story-setup/references/agent-references/writing-craft.md");
  const marker = "## 11. 场面语法";
  const text = await readFile(target, "utf8");
  if (text.includes(marker)) return;
  const section = await readFile(join(overlayRoot, "writing-craft-section-11.md"), "utf8");
  const body = section.endsWith("\n") ? section : `${section}\n`;
  const prefix = text.endsWith("\n") ? "\n" : "\n\n";
  await writeFile(target, `${text}${prefix}${body}`);
}

export async function applyStoryCraft(): Promise<void> {
  for (const [sourceName, relativePath] of copies) {
    const target = join(ohStoryRoot, relativePath);
    await mkdir(dirname(target), { recursive: true });
    await copyFile(join(overlayRoot, sourceName), target);
  }
  for (const entry of replacements) await replaceOnce(entry);
  await appendSection11();
}

const invokedDirectly = process.argv[1] !== undefined
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

if (invokedDirectly) {
  await applyStoryCraft();
  const manifest = await refreshBundledManifest();
  process.stdout.write(`Applied story craft. Manifest tracks ${String(manifest.files.length)} files.\n`);
}
