## 概述
Agent Prompt是一个**分层、有缓存策略、支持动态注入的行为控制系统**，在有限的上下文窗口里让模型始终能”看到“最重要的信息

## Prompt模块化
如果只是一个大字符串，容易牵一发动全身，不利于维护
```ts
const systemPrompt = `你是一个代码助手。
帮用户完成编程任务。先读文件再修改。
不要加没被要求的功能。执行危险命令要确认。
输出要简洁，不要用 emoji……`
```
可以把prompt拆成独立的section，每个都职责单一
- 独立修改：改『输出风格』不会影响『行为规则』
- 条件组装：某些section可以根据环境决定要不要包含
- 缓存友好
```ts
// 每个 section 是一个独立的字符串，最后拼成数组
const systemPrompt = [
  identitySection(),      // "你是 XX，负责 YY"
  systemRulesSection(),   // 环境约束：权限、压缩、标签
  taskGuidelines(),       // 做事方式：先读再改、不过度发挥
  riskGuidelines(),       // 行动准则：什么操作要确认
  toolUsageGuide(tools),  // 工具指南：根据实际工具列表动态生成
  outputStyle(),          // 输出风格：简洁、格式要求
]

```
也可以使用更优化的Prompt Pipe，每个section都是一个函数，接收当前的上下文信息（用户状态、可用工具等），用于判断是否需要输出内容
每个Pipe都是一个独立的文件，逻辑自包含，新加Pipe也不会改任何已有代码；每个Pipe都是纯函数，mock一个context就能独立测试
参考🌰：
- 核心规则Pipe：不依赖任何上下文，始终返回
```ts
// prompt-pipes/core-rules.ts
export const coreRules: PromptPipe = () => `## Core Rules
1. 先读文件再修改，不要凭记忆改代码
2. 不要加没被要求做的功能
3. 三行相似代码比过早抽象好
...`
```
- 条件返回Pipe：工具配合用完了才返回内容
```ts
// prompt-pipes/tool-availability.ts
export const toolAvailability: PromptPipe = (ctx) => {
  const notices: string[] = []
  if (!ctx.webSearchEnabled) {
    notices.push('搜索工具不可用，用户配额已满。不要尝试搜索。')
  }
  if (notices.length === 0) return null  // 没有限制则不需要
  return `## Tool Availability ${notices.join('\n')}`
}
```

## 缓存
selection有两类内容：
- 静态内容：身份定义、行为规则、输出风格等，对所有用户和项目都一样
- 动态内容：用户的自定义规则、当前工作目录等，每个用户、每次会话都不同

需要在动态和静态之间画一条明确的边界线：静态部分全部放前面，做全局缓存，命中率高；动态部分放后面，变化只影响自身，不影响前面的缓存

## 自定义Agent行为
Claude Code用CLAUDE.md注入用户自己的规则，核心设计原则：
- 越通用的配置优先级最低，越具体的优先级越高
- 低优先级先加载，高优先级后加载，因为模型对prompt末尾的注意力更强

即：用户偏好<项目规则<本地覆盖；在注入用户配置时，要明确告诉模型“这些指令覆盖默认行为“

参考🌰：
- ~/.claude/CLAUDE.md（用户全局，跨项目生效）：用pnpm不用npm
- 项目根目录/.claude/CLAUDE.md（项目级，提交到 Git，团队共享）：组件放xxx、页面放xxx
- CLAUDE.local.md（本地私有，不提交 Git）：在重构xx模块，改动时要特别小心

## 高频信息
有些每轮都在变的信息，如：IDE打开的文件、当前任务相关的Skill等，如果塞进system prompt就会破坏缓存，需要**在对话消息流里注入**

🌰：实际的消息结构
模型会理解`<system-context>`里的内容是辅助信息，不是用户说的话
可以用任何 XML 标签，只要在 system prompt 里提前告知模型这些标签的含义就行
```ts
// 用户实际发送的消息
const userMessage = "帮我看看 auth.ts 有什么问题"

// 系统在发送给模型之前，会在消息里注入额外上下文
const enrichedMessage = `
<system-context>
当前 IDE 打开的文件：src/auth.ts (第 42 行)
相关 Skill：@security-review（安全审查最佳实践）
今天日期：2026-04-07
</system-context>

帮我看看 auth.ts 有什么问题
`
```
消息内注入的好处：
- 不影响system prompt缓存
- 每轮内容可以不同，随着当前上下文动态变化
- 不额外增加轮次，附加在已有的用户消息里，不打乱对话结构

## 可插拔的上下文引擎
> 不同的场景可能需要不同的上下文策略：有的需要RAG检索历史对话、有的需要激进压缩、有的需要多会话共享上下文

OpenClaw把上下文管理抽象成一个可插拔接口
assemble 返回的 systemPromptAddition 意味着上下文引擎不只管消息历史，还能动态影响模型的行为指令，功能非常灵活
```ts
interface ContextEngine {
  // 会话开始：导入历史上下文
  bootstrap(sessionId: string): Promise<void>

  // 每条消息进来：存入引擎
  ingest(message: Message): Promise<void>

  // 组装上下文：在 token 预算内选最相关的内容
  assemble(messages: Message[], tokenBudget: number): Promise<{
    messages: Message[]           // 组装好的消息列表
    systemPromptAddition?: string // 可选：动态追加到 system prompt
  }>

  // 超限时压缩
  compact(tokenBudget: number): Promise<void>

  // 每轮结束后清理
  afterTurn(): Promise<void>
}
```
默认实现是简单的透传，把消息列表原样给模型，但也可以替换成任何策略，比如RAG召回：
```ts
// 用向量数据库做 RAG 检索
class RAGContextEngine implements ContextEngine {
  async assemble(messages, budget) {
    // 不是把所有历史消息都塞进去
    // 而是用语义检索找出最相关的历史片段
    const relevant = await this.vectorDB.search(
      messages[messages.length - 1].content,
      { topK: 10, budget }
    )
    return { messages: [...relevant, ...recentMessages(messages, 5)] }
  }
}
```

## Context Rot 上下文腐化
### Agent”失忆“
Agent在轮次较多后会做出莫名其妙的决策：忘了之前读过的代码、重复之前已经做过的操作等
这是因为模型对上下文头部和尾部的注意力最强，中间的内容会被逐渐忽略，上下文越长，中间的盲区越大

### 上下文焦虑
当模型感知到上下文快满了，它会主动偷懒：跳过步骤、简化回答、不再调用工具去验证

### 内容控制
模块化、缓存分层、消息注入等本质都是**为了控制入口，减少不必要的上下文消耗**
- 入口管理：Pipe里没用的section返回null会直接消失
- 静态/动态分割线：把宝贵的上下文空间留给真正有用的信息
- 消息内注入只附带当前相关的信息，不是把所有Skill、Memory都塞进去

**与其等上下文爆了再去压缩，不如一开始就少放东西**

### 任务清单
Claude Code 有个 Task 工具，模型可以把任务清单写到一个文件里，**写任务清单这个动作本身帮模型"聚焦注意力"**
- 它把散落在上下文各处的任务信息整理成了一个结构化的清单，相当于做了一次主动的"注意力操控"。模型后续做决策时，看的是这个清洁、结构化的清单，而不是从 50 轮杂乱的对话历史里翻找
- 有时候花一点 token 做注意力操控，总体效果反而更好。这跟"入口管理"不矛盾——省下来的空间，应该花在**真正帮助模型做好决策的信息**上