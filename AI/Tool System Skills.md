## 概述
核心理念：与其教模型使用新协议，不如用它最擅长的方式——读文档

## 渐进式加载
### Frontmatter
每个SKILL.md开头都有一个YAML frontmatter，Agent启动时只会加载这些信息，用于模型判断这个Skill跟当前任务有没有关系
```yaml
---
name: remotion
description: React 视频制作最佳实践
when_to_use: 当用户需要创建、编辑或渲染视频项目时
---
```

### 完整内容
当模型判断某个Skill跟当前任务相关时，才加载SKILL.md的完整内容，包括最佳实践、代码实例、常见陷阱等等

### 引用文件
Skill目录下还可以有references和scripts，这些文件不会主动加载，当模型需要使用的时候会通过Read工具去读

## Claude Code的Skills
### 用YAML控制Skill的行为边界
frontmatter不仅只是一个名字和描述，可以是一套**行为控制系统**
以一个部署到生产环境的Skill为🌰：
- allowed-tools：限定了权限边界，不能随便调用其他工具
- disable-modal-invocation：必须用户手动输入 /depoy-prod 才能触发
- context：隔离了执行环境，部署过程在一个独立的子Agent里跑，有自己的上下文窗口和token预算
- model：指定工作的模型，在一些确定性较大的流程里可以使用推理能力较弱的模型
- hooks：增加了执行前的拦截，是否阻塞取决于hook脚本的退出码
- paths：条件激活，只有在指定目录下工作时，模型才会有可能使用这个Skill
```yaml
---
name: deploy-prod
description: 部署当前分支到生产环境
when_to_use: 当用户明确要求部署到生产时
allowed-tools:
  - Bash(git:*)
  - Bash(kubectl:*)
disable-model-invocation: true
context: fork
model: sonnet
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - command: "echo '即将执行: '$TOOL_INPUT' ' >&2 && exit 2"
paths:
  - deploy/**
  - k8s/**
---
```

### context注入
在SKILL.md里可以嵌入shell命令，用！前缀标记
Skill 被激活时，这些命令会实时执行，结果注入到 Skill 内容里，这意味着 Skill 不是一个静态的文档，而是可以动态感知环境
```markdown
当前 Git 状态：
!`git status --short`

当前分支：
!`git branch --show-current`
```

### 加载来源&优先级
如果团队和外部开发者都写了一个同名的Skill，来源决定优先级：Skill可以来自内置的、用户装的（项目级配置优于全局配置）、MCP Server转换的，优先级从高到低排序
其中MCP Server 提供的 Prompt 也能被自动转成 Skill 格式加载，但它的信任等级最低，像shell命令执行语法就被禁掉了，因为来自远程的内容不可信

## OpenClaw的Skills
### 安装配方
**Skill不只是知识，还需要工具**
一个Skill可能依赖外部工具，可以在SKILL.md里声明安装配方，系统会根据用户环境自动选择最合适的安装方式
```yaml
---
openclaw:
  install:
    - kind: brew
      formula: sherpa-onnx
      bins: [sherpa-onnx-offline-tts]
    - kind: node
      package: playwright
      bins: [playwright]
    - kind: go
      module: github.com/example/tool@latest
    - kind: uv
      package: some-python-tool
    - kind: download
      url: https://github.com/.../release.tar.gz
      extract: true
---
```

### 资格检查
不是每个Skill都适用于所有环境，一个macOS专属的Skill放到Linux上没法用
系统在加载时会检查这些条件：操作系统对不对、配置项开了没等，不满足的Skill直接跳过
```yaml
---
openclaw:
  os: [darwin, linux]
  requires:
    bins: [ffmpeg, ffprobe]
    anyBins: [chromium, google-chrome]
    env: [OPENAI_API_KEY]
    config: [browser.enabled]
---
```

### 安全扫描
Skill 的脚本是明文代码，可以被扫描、被审查、被 Git 追踪
使用 skill-scanner 工具，在安装时扫描 Skill 目录下的所有脚本文件（.js、.ts、.mjs 等），检测危险代码模式：
- critical 级别：高危操作，直接警告
- warn 级别：可疑模式，建议审查
- info 级别：信息提示

扫描结果会在安装过程中展示给用户，如果发现 critical 级别的问题，会有明确的警告

### 调用策略
Skill有两种调用模式：
- user-invocable：默认为true，用户可以通过`/skillName`命令手动触发
- disable-model-invocatgion：设为true后，模型不能自动触发，只能用户手动

## skill的分发生态
### Claude Code：Marketplace  + Plugin
用户可以通过`claude plugin marketplace`来管理skill来源，可以添加多个marketplace源，每个源都有一批经过审核的插件，每个插件可以包含一个活多个Skill；针对official marketplace和third-party在权限检查上享受不同的待遇，官方审核的Skill可以自动获得更高的信任等级

### OpenClaw：三层来源 + 跨设备感知能力
社区有专门的Skill市场（ClawHub），有三层来源：
- Bundled Skills：内置的，随OpenClaw一起发布，有`allowedBundled`配置控制启用
- Workspace Skills：项目目录下的`.openclaw/skills/`，跟着代码仓库走
- Remote Skills：从远程节点同步过来的Skill，跨设备共享

OpenClaw通过Gateway节点网络实现了**实时感知能力与分发，根据目标环境的实际能力，动态决定哪些Skill可用**
- 多台设备通过WebSocket连接到同一个Gateway，每个设备都会注册自己的信息（操作系统、设备类型、支持的命令列表）
- 当一个远程节点连接上后，OpenClaw会做一次Remote Bin Probe，会收集本地所有Skill声明所需要的二进制文件，然后向远程节点确认它能跑哪些Skill。这些信息会被缓存，在远程节点的二进制列表发生变化时自动触发整个Skill列表刷新

### 安装不只是复制文件
一个Skill从安装到可用，需要经历来源获取->安全审计->依赖安装->能力验证四道关卡
#### 第一步：下载Skill文件
支持从git仓库、HTTP URL等来源获取

####  第二步：安全扫描
安装完文件后，用skill-scanner扫描目录下的所有脚本文件，检测代码危险模式，分为critical、warn、info三级扫描结果

#### 第三步：依赖安装
根据SKILL.md里的安装配置，调用对应的包管理器安装依赖

#### 第四步：二进制验证
安装完依赖后，会检查需要的二进制文件是否真的可用，如果不可用会在安装结果里给出明确的失败信息

## Skill & MCP
###  本质区别
- MCP走的是协议标准化：定义一套通用协议，任何客户端都能接。好处是跨平台，坏处是协议本身的开销（进程、通信、认证、Token）
- Skills走的是"文件夹约定"：个文件夹、一个 Markdown、几个脚本。好处是简单、轻量、模型天然会用，坏处是没有标准化的跨平台协议

### 真实关系
Skills 是通用的"知识层"，但"能力层"用什么得看场景
#### 本地Agent：Skills + CLI
像Claude Code这种跑在用户本机，有完整的文件系统、shell和包管理器，SKILL.md 提供知识，模型直接通过 Bash 调用 git、ffmpeg等能力，不需要中间加一层 MCP 协议

#### 云端Agent：Skills + MCP
越来越多的 Agent 跑在云上：Web 应用里嵌的 Agent、移动端 Agent、API 服务型Agent；这些场景下没有本地文件系统，没有 shell 可以调，CLI 这条路走不通
生产环境的 Agent 需要连接 Salesforce、Google Drive、数据库这些外部服务，MCP 作为标准化的远程协议，就是解决这个问题的

#### 最佳实践：Skills + MCP
MCP Server捆绑发布Skills：Skills 负责"知道怎么做"，MCP 负责"能做到“

## Skill系统的设计原则
- 渐进式加载：初始加载只放摘要，完整内容按需加载
- 文件即配置：一个Markdown文件比JSON+Server进程的配置门槛低，利于其他人的生态贡献
- 知识比工具重要：与其给模型20个精确的工具调用，不如给一份最佳实践文档
- 安全前置保证：需要在Skill安装或加载时就检查，而不是等出了问题