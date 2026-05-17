## @commitlint/cli
`commitlint`检查提交消息是否符合提交格式
### 安装
```bash
yarn add @commitlint/{config-conventional,cli} -D
```
### 输出配置文件
```bash
echo "module.exports = {extends: ['@commitlint/config-conventional']}" > commitlint.config.js
```
## husky
通过`husky`的`commit-msg`钩子来触发提交前的内容校验
### 安装
```bash
yarn add husky --dev
```
### 激活钩子
```bash
yarn husky install
```
### 添加相应钩子
```bash
yarn husky add .husky/commit-msg 'yarn commitlint --edit $1'
```