# rank-bridge

只从 `novel_rank_scout` 抽出两类匿名 HTTP 榜单：起点移动榜、番茄榜单页。

`assets:craft` 把 `rankmin/` 铺到 `skills/story-long-scan/bridge/rankmin/`，并把 `rankmin_cli.py` 铺到同级 `bridge/`。发行构建会删掉 `skills/story-long-scan/scripts/`，所以采集代码不能放在 `scripts/` 下。

不包含：原始 HTML 落盘、桌面 WOFF、番茄字体表、详情页或章节补标题、开篇样本、七猫、晋江、刺猬猫。番茄书名仍是私用区字符时，函数失败并指出字段，不改去下作品页。
