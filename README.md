# 博客

个人技术博客，内容涵盖 AI、React、TypeScript、前端基础、工具链等。

Obsidian ↔ GitHub 双向同步。

## 使用

```bash
# 首次
python3 sync-blog.py setup

# 双向同步（先拉后推）
python3 sync-blog.py
```

设每日定时：`0 9 * * * python3 ~/Documents/blog-content-sync/sync-blog.py`
