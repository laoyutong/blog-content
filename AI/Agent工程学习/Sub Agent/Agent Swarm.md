## 概述

🌰：需要同时开发三个功能模块：用户认证、支付系统、通知服务。这三个模块有依赖关系，支付完成后要调通知服务，通知服务需要用户认证的 token。如果用父子模式，三个子 Agent 各干各的，互相不通信，最后合并的时候大概率接口对不上

Swarm 模式就是让多个Agent像团队一样协作：一组 Agent 组成一个团队，有一个 Leader 协调分工，成员之间可以互相发消息、共享任务列表、同步进度


## 模式差异
除了Agent数量的变化，架构层面多了三个难题
- **双向通信**：父子模式是单向的，父 Agent 给任务，子 Agent 返结果。但团队协作需要 Agent 之间互相发消息，这就需要一套消息传递机制，谁发给谁、怎么发、对方什么时候能收到
- **共享状态**：团队需要一个共享的任务列表，谁在做什么、做完了没有、还有哪些没人认领。多个 Agent 同时读写这个列表，就涉及并发控制，两个 Agent 同时认领同一个任务怎么办
- **权限代理**：单 Agent 的时候，遇到需要用户确认的操作），直接弹窗问用户就行。但 Swarm 里的 Worker Agent 可能跑在一个后台进程里，没有 UI。它遇到权限问题，得把请求转发给 Leader，Leader 再问用户，用户批准后再把结果传回 Worker

## 执行模式
Claude Code的Swarm同时支持三种teammate的执行后端，共享同一套 Mailbox、任务列表和团队文件

Claude Code 启动 teammate 时会检测当前环境：装了 tmux 就用 tmux，装了 iTerm2 就用 iTerm2，都没有就 fallback 到 in-process

### In-process
teammate和leader跑在同一个Node.js进程，用 AsyncLocalStorage 隔离上下文

好处是零启动延迟、通信走内存。坏处是一个 teammate 如果陷入死循环，会拖慢整个进程

teammate 的 AbortController **不链接到 Leader 的**，按 ctrl+c 中断 Leader，正在工作的 teammate 不会被杀掉，防止 Leader 的一次操作失误把所有人的工作都毁了

### Tmux
tmux可以在一个终端窗口里开多个独立面板，而Claude Code给每个teammate开一个面板，每个teammate就是一个独立的claude code进程

好处是真正的进程隔离，一个崩了不影响其他人。坏处是启动慢、通信走文件 I/O，比较适合长时间运行的重型任务

### iTerm2
跟 tmux 类似，但用的是 macOS 原生的 iTerm2 分屏

用户体验更好（能直接在 iTerm2 里看到每个 Agent 的输出），但只能在 macOS 上用


## 基于文件的消息系统
Claude Code使用**Mailbox**方案：每个 Agent 有一个"收件箱"，其他 Agent 往里面写消息，Agent 自己来读

具体方案：每个团队成员在磁盘上有一个 JSON 文件当收件箱，路径类似 `~/.claude/teams/{team-name}/inboxes/{agent-name}.json`。要给某个 Agent 发消息，就往它的收件箱文件里追加一条记录。Agent 在每轮 Agent Loop 的间隙检查自己的收件箱，有新消息就读取处理

SendMessage 工具支持三种发送方式：
- 指定某个 teammate 的名字发点对点消息
- 用 `*` 广播给所有人
- 发送结构化请求（比如关闭请求、计划审批）

Agent 不是实时监听收件箱的，而是在每轮 Agent Loop 的工具调用间隙检查一次。如果 Agent 正在执行一个耗时的工具调用，消息就得等这轮工具执行完才能被看到

文件 I/O 比内存通信慢，Claude Code 如果两个 Agent 跑在同一个进程里，就跳过文件 I/O，直接在内存里传递消息。具体来说，发送方把消息放进一个内存队列，接收方那边有一个 Promise 在等着，消息一到，Promise 立刻 resolve，接收方马上就能处理。这比读写文件快得多，延迟从毫秒级的磁盘 I/O 降到微秒级。只有跨进程的 Agent 才需要走磁盘

并发安全也是文件方案的一个痛点：两个 Agent 同时往同一个收件箱写消息，可能会互相覆盖。Claude Code 用文件锁 + 重试退避来解决，写入前先加锁，拿不到锁就等一等（从 5ms 开始，指数退避到 100ms，最多重试 10 次）


## 共享任务列表
团队需要一个共享的任务列表来协调分工。Claude Code 的做法是给每个团队创建一个独立的任务目录，所有成员通过团队名字解析到同一个目录

关键问题是并发控制，多个 Agent 可能同时想创建任务、认领任务、更新状态。Claude Code 的方案和 Mailbox 类似：文件锁 + 重试。不过参数更激进一些，最多 30 次重试，退避从 5ms 到 100ms，给 10 个以上并发 Agent 留了足够的重试预算

同一套代码要支持三种运行模式（in-process、tmux、iTerm2），需要保证所有 Agent 都找到同一个任务列表。Claude Code 是用**团队名字**作为任务目录的统一标识，不管 Agent 从哪种方式启动，只要拿到了团队名字，就能解析到同一个任务目录

## Permission Sync 
一个 Worker Agent 跑在 tmux 的后台 pane 里，没有 UI 交互能力。它需要执行一个 `rm -rf build/` 命令，按权限策略这个操作需要用户确认

Claude Code 的解法是**权限请求转发**：Worker 把请求写到一个 `pending` 目录，Leader Agent 定期轮询这个目录，看到请求后呈现给用户。用户批准或拒绝后，结果写入 `resolved` 目录，Worker 读取结果继续（或放弃）执行

如果 Worker 和 Leader 跑在同一个进程里（in-process 模式），就不需要走文件，直接共享内存中的 `ToolUseConfirmQueue`，Leader 立刻能看到请求，只有跨进程的情况才走文件中转


## 团队关闭流程
不能依赖Agent自己决定是否做完任务：Agent可能觉得自己的部分做完了，但其实还有测试没跑、文档没写、或者其他 Agent 依赖它的输出还没拿到

Claude Code 的方案是 **Leader 审批制关闭**：Worker 想退出时，先给 Leader 发一个 shutdown 请求。Leader 检查这个 Worker 的任务是否真的完成了，如果没完成，Leader 可以拒绝请求并告诉它还需要做什么。只有 Leader 确认后，Worker 才能真正退出

Leader 在发起全局 shutdown 之前，还会等所有 teammate 进入 idle 状态。每个成员有一个 `isIdle` 标记，Leader 注册回调函数等待所有人都 idle 了才开始关闭流程



## 其他方案
OpenAI Swarm是极简路线：Agent 通过函数调用直接把控制权"交接"（handoff）给另一个 Agent。没有中心节点，没有消息队列，一个 Agent 返回另一个 Agent 对象，系统就切换到那个 Agent 继续对话。共享的是对话历史，每个 Agent 用自己的 system prompt 和工具集来解读同一段历史。OpenAI 自己定义这个框架为"教学用途"，生产级的方案已经升级为 Agents SDK

[AutoGen](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html)使用GroupChat 模式：所有 Agent 在同一个聊天室里，一个 GroupChatManager 决定"下一个谁说话"。选人的策略可以是 LLM 决定（根据上下文判断谁最适合接话）、轮流、或者自定义规则。好处是所有 Agent 共享完整上下文，信息不会丢。坏处也很明显，上下文会快速膨胀，而且全靠 LLM 选下一个 speaker 本身就不太靠谱


## Swarm适合场景
- 多模块并行开发：三个独立但有接口依赖的模块同时推进，Agent 之间需要协商接口定义、同步进度。用父子模式做不了这种横向协调
- **长时间运行的复合任务**：比如一个持续几十分钟的大型重构，涉及前端、后端、测试多个维度。每个维度的 Agent 跑在独立进程里（tmux 模式），一个崩了不影响其他人的进度
- **需要人工审批的分布式工作流**：多个 Worker 各自推进，遇到高风险操作时通过 Permission Sync 机制把审批请求汇总到 Leader，用户在一个地方统一处理

**如果任务之间不需要互相通信，用父子模式就够了**，更简单、更可靠、更好调试
