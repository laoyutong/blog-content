# 博客

个人技术博客，内容涵盖 AI、React、TypeScript、前端基础、工具链等。

Obsidian ↔ GitHub 双向同步。

## 主电脑（Obsidian → GitHub）

编辑 Obsidian vault 中的 `博客/` 目录，每天 9:00 自动推送。

手动同步：`python3 sync-obsidian-to-github.py`

## 其他电脑（GitHub → Obsidian）

```bash
# 首次
git clone https://github.com/laoyutong/blog-content.git ~/Documents/blog-content-sync
python3 pull-blog-from-github.py setup

# 日后同步
python3 pull-blog-from-github.py
```

也可设定时任务：`0 9 * * * python3 ~/Documents/blog-content-sync/pull-blog-from-github.py`
