## 思路一：延迟加载 Deferred Tool Loading

### 两类工具会被延迟
- 第一类是MCP工具，因为是用户通过MCP Server接入的外部工具，数量不可控，而且大部分的对话用不上
- 第二类是标记延迟的内置工具
  - 核心工具：Read、Edit、Bash等几乎每次对话都要用，永远加载
  - 低频工具：WebSearch、Plan Mode等，增加`shouldDefer`标记

### 延迟工具的发现机制
模型的prompt里不是完整的工具Schema，而是一个工具名称的列表，类似于：
```
以下工具可用，但需要先通过 ToolSearch 获取完整定义：
WebSearch, WebFetch, NotebookEdit, LSP, CronCreate, CronList...
```
可以通过ToolSearch的元工具来获取，传入查询关键词或工具名，工具会返回匹配工具的完成Schema定义
支持三种查询方式：
- 精确选择： `select:Read,Edit,Grep` 直接按名字取
- 关键词搜索：`notebook jupyter` 模糊匹配
- 必选+排序：`+slack send` 名字里必须包含slack，按相关性排序

该流程依赖API支持`defer_loading`和`tool_reference`的特性
**具体的工作流程：**
1. 初始请求只发核心工具，在调用API之前会动态过滤工具列表（未被发现的延迟工具），模型只能看到一段名字列表："以下工具可用但需要先搜索：WebSearch……"
2. 模型发现需要WebSearch，就调用ToolSearch传入关键词。ToolSearch会返回`tool_reference`类型的内容块，包含工具名称，但没有完整的Schema，会放入到`tool_result`消息里作为对话历史的一部分
3. API看到`tool_reference`块，就会在模型的上下文里注入对应工具的完整Schema定义
4. 在构建每一轮请求前，会扫描整个对话历史，提取所有出现过的`tool_reference`块，构建一个已发现工具的集合，会被包含在`tools`参数里，API就可以展开他们的Schema了

不依赖API的方式：
- ToolSearch返回纯文本Schema，动态修改tools列表。但每次加入新工具，都会使KV Cache从工具定义的位置开始全部失效
- 工具代理模式：做一个固定的代理工具，模型把实际参数序列化后塞进去，agent拿到后根据tool_name路由到真正的工具，反序列化后再传进去。但这个方案通过文本描述来理解参数格式，复杂工具的准确率会较低，依赖模型的指令遵循能力
```json
{
  "name": "call_tool",
  "parameters": {
    "tool_name": { "type": "string" },
    "arguments": { "type": "string" }
  }
}
```

### 自动触发阈值
不是所有场景都需要延迟加载，当延迟工具的JSON Schema总量超过上下文窗口的10%时才启用延迟加载
低于这个阈值，所有工具正常加载，没有额外开销。高于这个阈值，自动切换到延迟模式

### PromptCache
- 延迟加载的工具不会参与Cache key的计算，会在源码里直接filter掉
- 新加载的Tool Schema会在对话历史（tool_result）里，而不是工具定义区域，不影响Prompt前缀

## 思路二：工具配置文件 Tool Profile
按场景预选，定义了四种Tool Profile，每个核心工具在定义时就标注了属于哪些Profile
- mininal：最基础的交互；session_status等
- coding：编程场景；read、write、edit等
- messaging：通讯场景；message、sessions等
- full：全部能力，包含所有的核心工具

### Tool Group 批量引用
工具可以按功能分组，配置时可以引用整个组，而不是逐个列出工具名
可预测，知道在每个场景下模型能使用什么工具；但不够灵活，如果coding场景需要发消息，就需要切换Profile
- group:fs → read, write, edit, apply_patch
- group:runtime → exec, process
- group:web → web_search, web_fetch
- group:memory → memory_search, memory_get
- group:sessions → sessions_list, sessions_history, sessions_send, sessions_spawn

### 与延迟加载的本质区别
延迟加载是**按需发现**：所有工具都可用，只是模型需要先搜索
工具配置文件是**按场景裁剪**：不在当前Profile里的工具，模型看不到也不能用

## 思路三：小工具集
从源头控制工具数量，用最少的工具覆盖最多的场景，复杂操作通过组合原子工具来实现
工作集分为三层：

### 第一层：原子工具
固定的、最小化的function calling工具集，类似file_write、bash、search等

### 第二层：CLI工具
通过sandbox暴露，遇到原子工具覆盖不了的能力，让模型通过bash调用系统命令
🌰：要用curl的时候，执行`bash("curl https://……")`

### 第三层：写脚本
更复杂的组合逻辑就让模型写 Python 或 Node.js 脚本放到 sandbox 里跑

## 思路权衡
| 维度 | Claude Code | OpenClaw Profile | Manus 小工具集 |
| :--- | :--- | :--- | :--- |
| **核心思路** | 按需发现 | 按场景裁剪 | 从源头控制 |
| **工具上限** | 无限，延迟加载的不占空间 | 由 Profile 决定 | ~20 |
| **Cache 影响** | 低，schema会注入到对话历史里 | 切换 Profile 会影响 | 极低 ，工具列表永远不变)|
| **额外开销** | 多一次 ToolSearch 调用 | 无 | 复杂操作需要多步组合 |
| **灵活性** | 最高 | 中等 | 最低但最可控 |
| **需要 API 支持** | 是 (defer_loading + tool_reference) | 否 | 是 (logit masking) |