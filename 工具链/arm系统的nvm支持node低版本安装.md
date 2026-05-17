> Note For Macs with the Apple Silicon chip, node started offering arm64 arch Darwin packages since v16.0.0 and experimental arm64 support when compiling from source since v14.17.0. If you are facing issues installing node using nvm, you may want to update to one of those versions or later.

在M系列的mac里，可以启动 x86_64 版本的 zsh
```
arch -x86_64 zsh
```
通过以下命令来验证
```
uname -m
```
要退出 x86_64 模式的 zsh 会话，只需输入：
```
exit
```