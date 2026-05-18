## Function Calling
模型不会调用任何函数，只会输出一段符合格式的JSON，具体执行由agent来做
1. 往API里塞了一组JSON Schema（工具菜单），描述每个工具叫什么、干什么、参数格式是什么
2. 模型看到了这份定义，结合用户的问题，坚决要不要使用某个工具
3. 如果要用，模型就会生成一段符合Schema的JSON
4. agent解析这个JSON，来执行真正的函数
5. 把执行结果塞回对话，模型看到结果后继续回复

## 约束解码
通过训练+约束解码的方式来保证输出合法的JSON，在选Token之前，把不合法的选项排除掉
- 把JSON Schema编译成一套语法规则
- 每生成一个Token，把不合法的Token概率设为0
- 剩下的合法Token重新归一化，正常采样
🌰：如Schema要求是string类型，当模型生成到`"city":`的时候，下一个Token只能是`"`

但只能保证格式，不保证语义。如city一定是string类型，但不一定是真实存在的城市

## 工具准确性
当工具数量上去之后，Function Calling的准确率会明显下降
- 注意力稀释：工具越多，每个工具的描述在上下文里占的比例越小，模型的注意力会被分散
- 语义膨胀：工具多了难免有功能类似的，模型容易搞混这种重复工具的工具
- 预算挤压：每个JSON Schema都塞进上下文，留给用户消息和对话历史的空间就少了

## 模型幻觉
模型有可能会生成假的参数，即工具幻觉：伪造文件路径、编造ID、猜测URL等
需要Schema设计和执行链路上防御：
- 用enum约束可选值
```json
{
  "action": {
    "type": "string",
    "enum": ["read", "write", "delete"]
  }
}
```
- 执行前校验
在真正调用函数之前，做一次业务级校验。比如文件路径：先检查文件是否存在；如果不存在，返回一个带有建议的错误信息
- 清晰的错误反馈
  - good case: "文件 /src/helpers/utils.ts 不存在。当前目录下有 /src/utils.ts 和 /src/lib/helpers.ts，你要找的是哪个？"
  - bad case: "ENOENT: no such file or directory" 
给了模型足够的信息来纠正自己

## Structured Output
Function Calling 本质上就是让模型输出一段符合特定格式的 JSON，而Structured Output让模型按固定格式输出
🌰：让模型打分
```json
{
  "score": 8,
  "issues": ["变量命名不规范", "缺少错误处理"],
  "pass": true
}
```
### 实际应用场景
1. 上下文压缩
agent上下文快满了需要压缩，可以强制输出格式
```json
{
  "summary": "用户要求重构 auth 模块，已完成 login/logout，待处理 token refresh",
  "key_decisions": ["使用 JWT 替代 session", "refresh token 存 httpOnly cookie"],
  "pending_tasks": ["实现 token refresh 端点", "添加 CSRF 防护"],
  "important_context": ["项目用 Next.js 14", "数据库是 PostgreSQL"]
}
```
这样压缩后的摘要是结构化的，后续 agent 可以精确地读取 pending_tasks 来继续工作，而不是从一段自然语言里「猜」还有什么没做完
2. 生成式UI
让模型基于 JSON Schema 来描述 UI 组件：
```json
{
  "type": "card",
  "title": "天气预报",
  "children": [
    { "type": "text", "content": "北京 · 晴 · 25°C", "style": "heading" },
    { "type": "chart", "data": [22, 25, 28, 26, 24], "labels": ["周一", "周二", "周三", "周四", "周五"] },
    { "type": "button", "label": "查看详情", "action": "navigate:/weather/beijing" }
  ]
}
```
前端拿到这个 JSON，直接渲染成真实的 UI 组件。模型不用写 HTML/CSS，只需要按 Schema 描述「我想要什么」，渲染层负责「怎么画」
3. 信息提取
从非结构化文本里提取结构化数据：
```json
{
  "name": "张三",
  "company": "某科技公司",
  "role": "CTO",
  "contact": "zhangsan@example.com"
}
```
### 使用选型
在模型需要自由推理的阶段强制 JSON 格式，反而会降低推理质量
通常的做法：
- 推理阶段（Agent 在思考下一步该做什么）：不用 Structured Output，让模型自由生成文本
- 动作阶段（Agent 决定调用哪个工具、传什么参数）：用 tool_use，约束输出格式
- 输出阶段（需要固定格式的结果）：用 Structured Output

## claude code的工具定义
一个工具的定义包含：
```
{
  name: "Read",                    // 工具名
  inputSchema: z.object({...}),    // Zod Schema，定义参数类型
  description(...),                // 动态描述，根据上下文变化
  call(...),                       // 真正的执行逻辑

  // 元数据——告诉系统这个工具的「性格」
  isConcurrencySafe(input),        // 能不能并发执行？
  isReadOnly(input),               // 只读还是会修改东西？
  isDestructive(input),            // 是不是不可逆的操作？
  validateInput(input),            // 执行前的业务级校验
  checkPermissions(input),         // 权限检查

  // 加载策略
  shouldDefer: true,               // 是否延迟加载（不塞进初始上下文）
  searchHint: "jupyter notebook",  // 关键词，帮助 ToolSearch 找到它

  // 结果处理
  maxResultSizeChars: 50000,       // 结果超过这个大小就存磁盘
}

```
相关的设计决策：
- inputSchema 用 Zod 而不是手写 JSON Schema：既能在编译时做类型检查，又能在运行时验证模型输出的 JSON
- isConcurrencySafe 依赖输入而不是工具本身：Read 工具总是可以并发的，但 Edit 工具要看具体编辑的是哪个文件——编辑不同文件可以并发，编辑同一个文件必须串行
- description 是个函数而不是字符串：工具描述可以根据上下文动态变化。🌰：在非交互式会话里（CI 环境），某些工具的描述会强调「不要请求用户输入」
- maxResultSizeChars 控制结果大小：结果不直接塞进对话历史，而是存到磁盘上，给模型一个摘要 + 文件路径，防止一次工具调用就把上下文撑爆

## 设计工具描述的实战建议
工具描述直接决定模型能不能选对工具、填对参数
1. 描述要详细，至少 3-4 句话
不要只写「获取天气」
```
"获取指定城市的当前天气信息，包括温度、湿度和天气状况。city 参数应该是城市名称（如'北京'、'上海'），不接受经纬度。只返回当前天气，不返回预报。如果城市不存在会返回错误"
```
2. 用命名空间前缀区分相似工具
命名空间前缀能显著减少语义碰撞
🌰：如果你同时有 GitHub 和 Slack 的工具，用 github_list_comments 和 slack_list_messages
3. description 比 type 更重要
模型在决定用哪个工具、怎么填参数的时候，主要看 description，不是看 type
把参数名叫 user 还是 user_id，description 写清楚「这是用户的唯一标识符，格式为 UUID」，比只标注 type: string 有效得多