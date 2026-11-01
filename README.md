# 博客

个人技术博客，内容涵盖 AI、React、TypeScript、前端基础、工具链等。

在线浏览：https://laoyutong.github.io/blog-content/

## 项目结构

- `AI/`、`React/`、`TypeScript/`、`基础/`、`工具链/`、`杂谈/`：Markdown 文章。
- `index.md`：首页。
- `quartz.config.ts`：站点配置、字体、颜色和内容处理插件。
- `quartz.layout.ts`：页面布局；目前使用浅色主题，不展示深色切换按钮。
- `quartz/styles/custom.scss`：自定义样式。
- `quartz/`：Quartz 4 引擎源码。
- `sync-blog.py`：Obsidian 笔记同步。
- `tests/`：同步脚本回归测试。
- `.github/workflows/deploy.yml`：GitHub Pages 部署流程。

内容直接位于仓库根目录，`content/` 空目录不参与构建。`public/` 是当前构建产物；`site/` 是旧 MkDocs 产物，不参与发布，两者均被 Git 忽略。

## 本地开发

需要 Node.js >= 22、npm >= 10.9.2；同步脚本使用 Python 3 标准库，无需额外依赖。

```bash
nvm use           # 使用 nvm 时先切换到项目 Node 版本
npm ci
npm run dev       # 本地预览，默认 http://localhost:8080
npm run build     # 构建到 public/
npm test          # Quartz 测试
npm run test:sync # 同步回归测试，使用临时本地 Git 仓库
```

`npm run docs` 是 `npm run dev` 的兼容别名。推送到 `main` 后，GitHub Actions 自动构建并发布到 `gh-pages` 分支。

## Obsidian 同步

默认笔记目录为 `~/Documents/Obsidian Vault/博客`，仓库目录为脚本所在目录。可通过环境变量 `BLOG_VAULT` 和 `BLOG_SYNC_DIR` 覆盖路径。

```bash
python3 sync-blog.py setup # 目标仓库不存在时克隆
python3 sync-blog.py       # 双向同步
```

同步前先提交或暂存工作区修改（`git stash`）；脚本会拒绝存在未提交修改的仓库，包括已暂存文件。仅同步 Markdown，排除 README、AGENTS、隐藏目录和引擎/构建/测试目录，不同步图片等附件。

同步先执行 `git pull --ff-only`，再根据上次成功同步的基线比较两端变化。首次同步保留两端独有的文件；同名文件内容不同则停止，需手动统一两端内容后重试。后续同步可传播单侧修改和删除；两端不同修改、删除与修改冲突均停止，不覆盖笔记。

基线保存在仓库 Git 目录下的 `blog-sync-state.json`，不提交到 Git。删除基线会重新按首次同步处理，无法再识别此前的删除。Git 操作失败会停止；推送失败后再次运行会重试已有提交。成功推送后才更新 Obsidian 和基线。

同步期间请暂停编辑笔记，并避免同时运行多个同步进程。脚本在网络操作后会检查笔记是否变化，但不提供编辑器级文件锁。
