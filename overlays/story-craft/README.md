# 长篇场面语法覆盖层

这份覆盖层只改长篇写作链。短剧、小说转游戏、视频解说不动。

`pnpm assets:sync:story` 会删掉 `packages/knowledge/oh-story` 再从 Oh Story 上游拷回。`scripts/apply-story-craft.ts` 在拷贝之后把本目录铺回去，并只重算 `manifest.json` 的文件哈希。上游仓库、commit、`skills/story/VERSION` 和 `agents_version` 保持同步结果。

没有上游检出时，直接跑 `pnpm assets:craft`。它只铺覆盖层并刷新哈希，不重新下载技能。

教材原文不进这个仓库。操作句在 `scene-grammar.md`。
