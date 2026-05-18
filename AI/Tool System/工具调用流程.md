## 一、参数格式验证
用Zod来验证模型输出的JSON内容，验证失败时会返回精确的错误路径，而模型需要这些信息来纠正自己的输出
```js
import { z } from 'zod'

// 工具定义里声明的 schema
const ReadSchema = z.object({
  file_path: z.string(),
  offset: z.number().optional(),
})

// 模型实际传过来的输入（file_path 类型错了）
const input = { file_path: 123 }

// 用 schema 校验
const result = ReadSchema.safeParse(input)
// result.success === false
// result.error 里精确指出：input.file_path: Expected string, received number
```

## 二、业务逻辑校验
需要对值本身做语义层面的检查，🌰：文件路径需要是绝对路径、编辑内容跟文件实际内容不匹配
在validateInput里实现，错误信息需要返回具体的原因+建议
```js
validateInput(input) {
  // 检查文件是否存在
  // 检查 old_string 是否在文件中能找到
  // 检查 old_string 是否唯一（不然不知道改哪个）
  // 如果不唯一，返回: "old_string 在文件中出现了 3 次，请提供更多上下文使其唯一"
}

```

## 三、输入补全&标准化
经过了验证和校验之后，输入在格式和语义上都没问题了，但可能还需要补充一些模型没有提供的信息
🌰：模型传了 file_path: "src/index.ts"。业务校验接受相对路径，但工具内部需要绝对路径，这一步就是把相对路径转成绝对路径

## 四、前置hook
用户自定义的脚本，在工具执行的关键节点触发
- 修改输入：把所有文件路径重写到一个沙箱目录
- 阻止执行：检测到rm命令就拒绝
- 注入额外上下文：附加一些模型需要知道的信息
```json
{
  "event": "PreToolUse",
  "command": "bash /path/to/my-check.sh $TOOL_NAME $TOOL_INPUT"
}
```
hook脚本的返回值决定了下一步动作：
- 0：继续
- 2（或输出JSON`{"decision": "block"}`）：阻止执行
- 输出JSON`{"updatedInput": {...}}`：修改输入后放行

## 五、权限检查
权限系统通常有三层，核心设计原则是：优先自动判定，减少打扰用户

### 规则匹配
根据预配置的规则决定
```json
{
  "allow": ["Read", "Glob", "Grep", "Bash(git *)"],
  "deny": ["Bash(rm -rf *)"]
}
```

### 分类器判定
对于规则没有覆盖到的情况，用一个轻量分类器来判断这次调用是否安全，用微小的一点延迟换来更高的安全性
结合当前的对话上下文和要执行的具体命令，通过一次轻量的 LLM 调用来评估这个操作是否安全，可以区分git status（只读查看）和git push --force（有风险的覆盖操作）

### 交互式询问
如果规则和分类器都没法决定，弹窗问用户【agent想执行npm instal xxx，允许吗？】，由用户来决定

## 六、工具执行
经过了前面五层过滤，输入终于被认为是安全的、合法的、已授权的，开始调用 tool.call()
需要对工具执行的结果进行处理

### 结果截断
工具返回的内容可能非常大，Read工具读取了一个1w行的文件，Bash工具执行会输出一个100kb的日志，如果都塞到对话历史，上下文直接就爆了
设置一个阈值，如果超过这个大小，结果就被存到磁盘上，对话历史里只放一个摘要+文件路径的引用
```
结果太大 → 存到 /tmp/tool_results/xxx.txt
对话历史里放："[结果已保存到文件，使用 Read 工具查看 /tmp/tool_results/xxx.txt]"
```

### 错误处理
模型需要的不是错误码，而是纠正所需要的上下文
- good case
```
文件 /src/helpers/utils.ts 不存在。
当前 /src/ 目录下有以下文件：
  - /src/utils.ts
  - /src/lib/helpers.ts
  - /src/common/utils.ts
```
- bad case
```
ENOENT: no such file or directory, open '/src/helpers/utils.ts'
```

## 七、后置hook
在工具执行完成后运行：
- 修改输出：过滤敏感信息
- 触发后续动作：工具修改了文件后自动跑lint
- 记录审计日志：追踪每一次工具调用的详情

## 工具并发调用方式
Claude Code依赖模型原生的parallel tool_use，在一次响应里可以直接输出多个tool_use块
OpenCode提供了Batch Tool的工具，模型调用batch工具，传入一组子调用，在应用层把这些子调用并行执行；同时模型不一定总会主动使用该工具，在描述里添加`USING THE BATCH TOOL WILL MAKE THE USER HAPPY`进行强烈暗示
```json
{
  "tool_calls": [
    { "tool": "read", "parameters": { "filePath": "src/a.ts" } },
    { "tool": "read", "parameters": { "filePath": "src/b.ts" } },
    { "tool": "grep", "parameters": { "pattern": "TODO" } }
  ]
}
```