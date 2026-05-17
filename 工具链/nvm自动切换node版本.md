## nvm配置
每个项目的根目录中创建一个名为 `.nvmrc`的文件，并在文件中指定所需的 Node.js 版本

## 终端配置
可以在 `~/.zshrc` 文件中添加类似的配置
```
autoload -U add-zsh-hook
load-nvmrc() {
  local nvmrc_path="$(nvm_find_nvmrc)"

  if [ -n "$nvmrc_path" ]; then
    nvm use
  else
    echo "No .nvmrc found in this directory or any parent directory."
  fi
}
add-zsh-hook chpwd load-nvmrc
load-nvmrc
```
然后通过 `source ~/.zshrc`重新加载即可生效