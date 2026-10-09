# rank-bridge

起点移动榜和番茄榜单页来自 `novel_rank_scout` 的匿名 HTTP。刺猬猫把 `ciweimao-api-reverse` 的协议客户端原样放在 `ciweimao_app/`：签名、解密、游客注册和 `Session.get_rank_books`。出口与采集器相同，静态地址用 `CIWEIMAO_PROXY_URL`，否则用快代理密钥提取一条 DPS。

`assets:craft` 把 `rankmin/` 铺到 `skills/story-long-scan/bridge/rankmin/`，并把 `rankmin_cli.py` 铺到同级 `bridge/`。发行构建会删掉 `skills/story-long-scan/scripts/`，所以采集代码不能放在 `scripts/` 下。

不包含：原始 HTML 落盘、桌面 WOFF、番茄字体表、详情页或章节补标题、开篇样本、验证码打戳、章节下载、七猫、晋江。番茄书名仍是私用区字符时，函数失败并指出字段，不改去下作品页。刺猬猫书名缺失时同样失败，不改去下章节。运行需要 `curl_cffi` 和 `pycryptodome`。
