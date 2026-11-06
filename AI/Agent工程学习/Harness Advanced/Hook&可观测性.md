## 问题
模型是非确定性的，同样的输入，Agent 可能给出不同的输出

一次任务可能跨 50 轮对话、20 次工具调用，调用链无比的长

 Agent 还有副作用——它写了文件、跑了命令、改了代码，这些操作不可逆


## Hook
不改源码就能定制Agent行为

Claude Code一共有27种事件类型，大概可以分为以下几组：
- **工具相关**：PreToolUse（工具执行前）、PostToolUse（工具执行后）、PostToolUseFailure（工具失败后）。这三个是最常用的，可以在工具执行前做安全检查，执行后自动 format，失败后记录日志

- **会话生命周期**：SessionStart（会话开始）、SessionEnd（会话结束）、Stop（Agent 要结束回复了）、UserPromptSubmit（用户提交消息）。这组 Hook 适合做统计和通知，比如会话结束时自动把结果推送到 Slack

- **上下文管理**：PreCompact（压缩前）、PostCompact（压缩后）。压缩时机很关键，PreCompact Hook 甚至可以阻止一次不合时宜的压缩（返回 exit code 2）

- **协作相关**：SubagentStart、SubagentStop、TeammateIdle、TaskCreated、TaskCompleted。Multi-Agent Swarm 场景用的，Leader 可以通过这些 Hook 追踪每个 teammate 的状态

- **文件和工作区**：FileChanged（文件被修改）、CwdChanged（工作目录切换）、WorktreeCreate/WorktreeRemove（Worktree 创建/删除）。这组 Hook 能监控 Agent 对文件系统的操作，比如在 FileChanged Hook 里记录 Agent 改了哪些文件，方便事后来审查

### 执行机制
Agent 触发事件时，把事件的上下文信息（工具名、参数、结果等）以 JSON 格式通过 stdin 传给 Hook 脚本，脚本处理完通过 exit code 告诉 Agent 下一步怎么走：
- exit 0：放行，一切正常
- exit 2：阻塞，把 stderr 的内容作为错误信息返回给模型
- 其他 exit code：非阻塞性错误，只给用户看，不影响 Agent 继续工作

**Hook 是外部 shell 命令，不是代码内部的回调函数**，所以不需要导入 Agent 的 SDK、不需要理解 Agent 的内部结构，写个 bash 脚本就能用。这跟 Git hooks 的设计思路是一样的，`.git/hooks/pre-commit` 就是一个普通的可执行文件

Hook 还支持 **async 模式**：脚本在后台执行，不阻塞 Agent 的主循环。通常用于不影响 Agent 下一步决策的操作，比如发通知、记日志、推送到外部系统。默认 Hook 有 10 分钟的超时限制，超时了会被强制终止

### 应用场景
- **自动 lint**：在 PostToolUse 挂一个脚本，每次 Edit 工具修改了文件后自动跑 `eslint --fix`。Agent 改完代码，格式自动就对了，不需要浪费一次模型调用来做格式化

- **安全拦截**：在 PreToolUse 挂一个脚本，检查 Bash 工具要执行的命令。遇到 `rm -rf`、`DROP TABLE` 这类危险操作直接 exit 2 阻塞，把"这个操作被安全策略禁止"返回给模型

- **完成通知**：在 Stop 事件挂一个脚本，Agent 完成任务后自动发一条飞书消息通知

- **CI 触发**：在 PostToolUse 挂一个脚本，每次 Agent 提交了 Git commit 后自动触发 CI 流水线。Agent 改代码、跑测试、提交，CI 自动启动，整个链路无人值守。这个场景在 Swarm 模式下更有价值，多个 Worker 各自提交代码，CI 自动在后台验证每一次提 commit


### 安全边界
Claude Code 的安全模型明确禁止了：Hook 配置是只读的，Agent 在会话期间无法修改。否则Agent 遇到一个被 Hook 阻止的操作，它可能会尝试修改 Hook 配置来绕过限制

Claude Code 还支持 **HTTP Hook**（向指定 URL 发 POST 请求）和 **Agent Hook**（用另一个 LLM 来评估当前操作是否应该放行）。HTTP Hook要求显式声明允许传递的环境变量（`allowedEnvVars`白名单），防止 API Key 之类的敏感信息通过 Hook 泄露到外部

## 可观测性
一整套监控体系，需要知道Agent 整体在干什么、花了多少钱、哪些环节是瓶颈

### 行业工具
- **AI Gateway**（如 [Helicone](https://www.helicone.ai/)、[Portkey](https://portkey.ai/)）：在应用和模型 API 之间的代理层。它能自动记录每一次 API 调用的 token 数、耗时、成本，还能加缓存、限流、多提供商路由
- **可观测性平台**（如 [Langfuse](https://langfuse.com/)、[LangSmith](https://www.langchain.com/langsmith/observability)、[Arize Phoenix](https://phoenix.arize.com/)）：通过 SDK 嵌入你的代码，追踪 Agent 执行的完整路径。
```ts 
// 以 Langfuse 为例，在每次 LLM 调用时加几行追踪代码

// 通过 OpenTelemetry（一套开源的可观测性标准，定义了 trace、span 等数据格式，让不同工具之间的追踪数据可以互通）自动追踪，不需要手动在每次调用前后加代码
// 初始化的时候注册一个 span processo
import { NodeSDK } from "@opentelemetry/sdk-node"
import { LangfuseSpanProcessor } from "@langfuse/otel"

const sdk = new NodeSDK({ spanProcessors: [new LangfuseSpanProcessor()] })
sdk.start()

// 在 Vercel AI SDK 的 streamText 里打开 telemetry 就行
const result = await streamText({
  model,
  messages,
  experimental_telemetry: { isEnabled: true, functionId: "agent-task" },
})
```


### 指标监控
- **Cache命中率**：Agent 每次对话的 Cache 命中率都很低（比如低于 50%），说明你的上下文前缀不够稳定，可能是 system prompt 在变、工具列表在变、或者对话结构不够一致
- **死循环和重复工具调用**：自动识别这种「重复调用同一个工具、传同样参数的循环」的模式并告警
