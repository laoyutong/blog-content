## 概述
ACP（[Agent Client Protocol](https://agentclientprotocol.com/)）标准化了"任何客户端"和"任何 Agent"之间的通信协议。写一次 Agent，所有支持 ACP 的客户端都能接

ACP 解决的是**外部系统怎么驱动你的 Agent**

## 交互流程
客户端启动 Agent 作为子进程，通过 `stdin` 发消息、`stdout` 收消息，消息格式是 `JSON-RPC 2.0`（每条消息一行 JSON）

1. 握手
客户端和 Agent 交换 `initialize` 消息，互相声明自己支持哪些能力（capabilities）
2. 创建会话
客户端发一个 `newSession` 请求，Agent 返回 session ID
会话之间互相独立，关掉客户端再打开，用 `loadSession` 就能恢复
3. 发指令、流式返回
 prompt 发过去之后，Agent 边干边推送 `sessionUpdate`，先推 token（看到 Agent 在"打字"），然后推一条"我要调用 read_file 读取 utils.ts"的状态更新，工具跑完继续推
4. 权限请求
Agent 准备修改 `xxx.ts` 了，写文件是敏感操作，会发一个 `requestPermission`，客户端弹确认框，点击允许后Agent再继续
5. 返回结果
修改完成，推送最终结果


## 接入示例
骨架就是三个方法：`initialize`（握手）、`newSession`（建会话）、`prompt`（干活）
流式推送用 `connection.sessionUpdate`
请求授权用 `connection.requestPermission`
```ts
import * as acp from "@agentclientprotocol/sdk";
import { Readable, Writable } from "node:stream";

class MyAgent {
  connection: acp.AgentSideConnection;

  constructor(connection: acp.AgentSideConnection) {
    this.connection = connection;
  }

  // 1. 协议握手——告诉客户端你支持什么能力
  async initialize() {
    return { protocolVersion: acp.PROTOCOL_VERSION, agentCapabilities: {} };
  }

  // 2. 创建会话——每个对话一个独立的 session
  async newSession() {
    return { sessionId: crypto.randomUUID() };
  }

  // 3. 处理用户指令——这是核心
  async prompt(params: acp.PromptRequest) {
    // 流式推 token 给客户端
    await this.connection.sessionUpdate({
      sessionId: params.sessionId,
      update: {
        sessionUpdate: "agent_message_chunk",
        content: { type: "text", text: "正在分析你的代码..." },
      },
    });

    // 遇到敏感操作，请求用户授权
    const result = await this.connection.requestPermission({
      sessionId: params.sessionId,
      toolCall: {
        toolCallId: "call_1",
        title: "修改 config.json",
        kind: "edit",
        status: "pending",
        locations: [{ path: "/project/config.json" }],
      },
      options: [
        { kind: "allow_once", name: "允许", optionId: "allow" },
        { kind: "reject_once", name: "拒绝", optionId: "deny" },
      ],
    });

    if (result.outcome.outcome === "cancelled") {
      return { stopReason: "cancelled" };
    }

    return { stopReason: "end_turn" };
  }
}

// 通过 stdin/stdout 跟客户端通信
const stream = acp.ndJsonStream(
  Writable.toWeb(process.stdout),
  Readable.toWeb(process.stdin)
);
new acp.AgentSideConnection((conn) => new MyAgent(conn), stream);
```


## A2A
接入Agent的客户端，本身也是一个Agent

核心：
- Agent Card：一份自描述，包括我是谁、服务端点在哪、有哪些技能（skills）、需要什么认证。别人的 Agent 先抓你的名片，确认你能干这活、谈妥认证方式，然后才开始对话
- Task 一次有状态的委托：客户端 Agent 发起一个 Task，远端 Agent 接单后，Task 沿着状态机走，包括提交、执行中、需要补充输入（远端 Agent 干到一半可以停下来反问，等客户端 Agent 补完信息再继续）、完成或失败
- Artifact：任务完成后，远端Agent交付的是结构化的产出物，内部推理、上下文等不会暴露