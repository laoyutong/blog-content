## 概念
Modal Context Protocol 模型上下文协议
类似于USB接口之于硬件，通过一个通用的协议，只要数据源（figma、github等）支持了MCP标准，任何支持了MCP的AI客户端（cursor、claude code）就能直接访问

### 解决痛点
- 数据孤岛：代码在IDE里，笔记在文档里，日程在日历里，AI很难同时获取这些背景信息
- 重复造轮子：每个AI应用都要为同一种数据源写一遍接入代码
- 隐私&安全：MCP允许在本地运行服务器，AI只在需要的时候请求特定的本地数据，更加安全

## MCP客户端
### 工作流程
1. 读取配置的MCP Server列表
2. 对每个配置创建Client来连接；通常使用stdio进行本地通讯，或者使用SSE进行远程通讯
3. 获取MCP的tools列表，转换成模型需要的tools结构；tool_choice设置auto，让模型选择是生成消息还是调用tool
```js
type: 'function',
function : { name: 'xxx', description: 'xxx', parameters: {} }
```
4. 通过Function Calling来决定调用哪一个tool
- 如果返回tools_call，则调用mcp.callTool，将调用结果追加进messages里，带上完整的tools和更新后的messages再次请求
- 如果直接返回content，则将结果流给用户

## 优化方案
> 参考anthropic的文章 [code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp)

### 核心挑战
传统MCP的使用方式在处理大规模或复杂任务时存在主要痛点：
- Token膨胀：所有的工具定义和每一个工具的返回结果都会塞进LLM的上下文窗口。如果系统的工具数量较多，仅加载定义就可能消耗数万个Token，响应缓慢且浪费Token
- 多步调用低效：Agent链式调用多个工具时，中间过程的所有原始数据都会在模型和服务之间往返，浪费Token且容易导致模型出错或超出上下文限制

### 解决方案
让模型编写并运行一段代码来操控这些工具，在安全的沙盒环境执行，来与工具进行交互
- 按需加载：模型不再预先加载所有工具定义，而通过文件系统或搜索，只加载当前任务真正需要的工具定义
- 高效数据处理：可以在执行环境中直接对数据进行过滤、聚合和转换后再返回给模型，避免无效数据污染上下文
- 隐私保护：敏感数据可以在执行环境中直接流转，确保核心隐私数据不会进入模型的上下文
- 更强控制流：可以通过for循环或if-else逻辑来处理批量任务，无需频繁在”模型推理“和”外部工具“之间切换，降低延迟
- 状态保持：Agent可以将中间结果写入文件，方便后续任务或其他Agent使用，实现了和类似长期记忆的效果

### 具体执行步骤
以 @modelcontextprotocol/server-filesystem 为例
1. 自动化生成的工具SDK
根据MCP Server的list_tools自动生成的代码，让模型知道有哪些API可以调用
```ts
/**
 * 自动生成的 FileSystem MCP SDK
 * 作用：为模型提供类型提示和调用接口
 */
export const mcp = {
  /** 读取文件内容 */
  async read_file(args: { path: string }): Promise<string> {
    // 运行时由执行器拦截并调用真实 MCP Server
    return await __call_mcp__("read_file", args);
  },

  /** 写入文件内容 */
  async write_file(args: { path: string, content: string }): Promise<void> {
    return await __call_mcp__("write_file", args);
  },

  /** 列出目录下的文件 */
  async list_directory(args: { path: string }): Promise<string[]> {
    return await __call_mcp__("list_directory", args);
  }
};
```
2. 模型编写的逻辑代码
当用户提出问题：”把src目录下所有的txt文件合并到dist/total.log里“
模型不会返回多个JSON的指令，而是直接返回一段TS代码
```ts
// 模型生成的逻辑块
async function task() {
  const srcPath = "./src";
  const distPath = "./dist/total.log";

  // 1. 获取目录列表
  const files = await mcp.list_directory({ path: srcPath });

  // 2. 在本地过滤和处理逻辑（核心优化：不需要模型干预循环）
  let combinedContent = "";
  for (const file of files) {
    if (file.endsWith(".txt")) {
      const content = await mcp.read_file({ path: `${srcPath}/${file}` });
      combinedContent += `--- File: ${file} ---\n${content}\n\n`;
    }
  }

  // 3. 写入最终结果
  await mcp.write_file({ 
    path: distPath, 
    content: combinedContent 
  });

  return { status: "success", filesProcessed: files.length };
}

// 执行任务并返回
task();
```
3. 构建沙盒
- 创建上下文：定义一个空对象，只把允许模型访问的API和伪造的mcp对象放进去
- 代码包装：将模型返回的代码包装在一个async函数里，确保能正确处理await
- 运行&捕获：执行代码并获取return的内容
4. 中间件拦截
模型在代码里是`await mcp.read_file({path: 'xxx'})`，需要拦截这个调用，将其转换成MCP协议定义的请求
具体实现方式：可以用Proxy对象来动态拦截
```js
import { Client } from "@modelcontextprotocol/sdk/client/index.js";

/**
 * 创建一个拦截器代理
 * @param mcpClient 真实的 MCP 客户端实例（负责发送 JSON-RPC）
 */
function createMcpInterceptor(mcpClient: Client) {
  return new Proxy({}, {
    // 当模型代码尝试访问 mcp.xxx 时触发
    get(target, propName: string) {
      // 返回一个异步函数给沙盒里的代码执行
      return async (args: any) => {
        console.log(`[拦截器] 检测到调用工具: ${propName}, 参数:`, args);

        // --- 拦截逻辑开始 ---
        try {
          // 1. 协议转换：将 TS 函数调用转为 MCP 调用的 JSON 格式
          // 2. 真实执行：通过长连接（stdio/http）发给真实的 MCP Server
          const result = await mcpClient.callTool({
            name: propName,
            arguments: args
          });

          // 3. 结果解包：MCP 返回的是 { content: [...] }，我们要把纯数据给模型
          return result.content[0].text; 
        } catch (err) {
          console.error(`[拦截器] 工具执行失败: ${propName}`, err);
          throw err; // 抛出错误，让沙盒里的 try/catch 能捕获
        }
        // --- 拦截逻辑结束 ---
      };
    }
  });
}
```
5. 把本地代码运行后的return结果发回给LLM