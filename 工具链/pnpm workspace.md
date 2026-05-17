## 配置文件
在根目录新建 `pnpm-workspace.yaml`
```yaml
packages:
  - 'packages/**'
```
## 安装依赖
想要安装在根目录，需要加上`-W(--ignore-workspace-root-check)`
```bash
pnpm add lodash -W
```
想给单独的包安装依赖，安装命令增加参数 `--filter <pkg name>`即可
```bash
pnpm add lodash --filter pckA
```
## 使用依赖
在`package.json`里写入相应的依赖
```json
 "dependencies": {
    "b": "workspace:*"
  },
```
或者在相应的包目录通过命令行安装
```bash
pnpm add b --workspace
```