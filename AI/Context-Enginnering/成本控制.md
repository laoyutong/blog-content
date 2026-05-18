## Cache的三个层次
### KV Cache: 模型推理层

模型要对整个输入做 Attention 计算，算出每个 token 和其他所有 token 的关系。这个计算非常昂贵
KV Cache：**如果这次发的输入和上次有一段共同的前缀，那这段前缀的 Attention 计算结果可以直接复用，不用重新算**

### Prompt Cache: API层

Prompt Cache 是 API 提供商提供的一个**计费优化**：如果请求里有一段内容之前发过，API 只会收一个大幅折扣的"缓存读取"价格
#### 缓存模式
##### **隐式缓存**
代码什么都不用改，API 自动检测前缀匹配，但**隐式缓存的命中率是概率性的，不是 100% 确定的**
##### 显式标记缓存
要在请求里标记 `cache_control`，告诉 API 哪些内容要缓存
```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 1024,
  "system": [
    {
      "type": "text",
      "text": "你是一个代码助手。以下是行为规则……（几千 token 的规则）",
      "cache_control": { "type": "ephemeral" }  // 👈 关键：标记缓存断点
    }
  ],
  "messages": [
    { "role": "user", "content": "帮我看看 auth.ts" }
  ]
}

```
##### 显式创建对象缓存
先调 API 创建一个 cache 对象拿到 ID，后续请求带这个 ID。适合大段固定知识库的场景，但额外收存储费
```ts
import { GoogleGenAI } from '@google/genai'

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY })

// Gemini 的显式缓存：先创建一个 cache 对象
const cache = await ai.caches.create({
  model: 'gemini-2.5-flash',
  contents: [{
    role: 'user',
    parts: [{ text: '这是一本 10 万字的技术文档……' }]
  }],
  ttl: '3600s'  // 缓存 1 小时
})

// 后续请求引用这个 cache
const response = await ai.models.generateContent({
  model: 'gemini-2.5-flash',
  contents: '基于上面的文档，帮我总结第三章的核心观点',
  cachedContent: cache.name  // 👈 引用缓存
})
```


### Context Collapse：应用层

思路：**与其真的把老消息删掉或压缩，比如把它们"折叠"起来**。老消息存到一个外部存储里，上下文里只保留一个折叠标记。需要的时候可以"展开"恢复。



## 路由模式
对于比较小的、轻量的任务，我们路由给更小的模型去做，可以有效地节省成本

### 策略
- **按任务类型静态路由**：在代码里写死分发逻辑，比如 Explore 操作就是用稍微逊色的 Sonnet 模型。这种做法简单，确定性高，适合任务类型明确的 Agent
- **按难度动态路由**：一个轻量级分类器实时判断每个 prompt 的复杂度，简单的派给便宜模型，复杂的派给贵模型

### 选型
对于大部分 Agent 产品，不需要训练分类器，在代码里按角色分配模型就行
- **Agent Loop 主推理**（代码生成、Bug 修复、架构决策）=> 走大模型
- **后台辅助任务**（对话摘要压缩）=> 用小模型
- **只读的 Sub Agent**（代码搜索、文件探索）=> 用小模型