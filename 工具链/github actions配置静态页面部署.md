# github actions自动部署静态页面
## 实现目标
每次push代码的时候，自动打包并更新至github pages中
## 解决方案
添加github actions
- 在仓库里新建`.github/workflows/main.yml`的文件
```yml
name: Deploy GitHub Pages
on:
  push:
    branches:
      - master
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v2

      - name: Build
        run: npm install && npm run build

      - name: Deploy
        uses: JamesIves/github-pages-deploy-action@v4.4.1
        with:
          token: ${{ secrets.ACTION_WORKFLOW }}
          branch: gh-pages
          folder: dist

```
- 配置仓库的secret token
在相应仓库`Settings`里`Secrets and variables`下的`Actions`里新增一个`respository secret`：
`name`：对应`yml`文件里`token: ${{ secrets.ACTION_WORKFLOW }}`里的`ACTION_WORKFLOW`
`secret`：在`Developer settings`里配置的带有`workflow`的`personal access token`

# 注意事项
- 如果是`vite`项目需要修改公共基础路径
```javascript
export default defineConfig({
  base: "./",
});

```