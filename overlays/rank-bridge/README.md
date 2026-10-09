# rank-bridge

起点移动榜和番茄榜单页来自 `novel_rank_scout` 的匿名 HTTP。刺猬猫只取 App 排行 `/bookcity/get_rank_book_list`，会话读环境变量。

`assets:craft` 把 `rankmin/` 铺到 `skills/story-long-scan/bridge/rankmin/`，并把 `rankmin_cli.py` 铺到同级 `bridge/`。发行构建会删掉 `skills/story-long-scan/scripts/`，所以采集代码不能放在 `scripts/` 下。

不包含：原始 HTML 落盘、桌面 WOFF、番茄字体表、详情页或章节补标题、开篇样本、游客注册、验证码、章节解密、七猫、晋江。番茄书名仍是私用区字符时，函数失败并指出字段，不改去下作品页。刺猬猫缺会话或书名时同样失败，不改去下章节。
