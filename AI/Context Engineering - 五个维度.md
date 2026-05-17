## 概览
| 维度 | 核心问题 | 做什么 |
| :--- | :--- | :--- |
| **Offload（卸载）** | 上下文太挤了 | 把信息搬到上下文之外（文件、数据库） |
| **Reduce（压缩）** | 上下文太大了 | 就地缩小（Compaction）或用摘要替换（Summarization） |
| **Retrieve（检索）** | 需要的信息不在上下文里 | 从外部按需取回（RAG、文件读取） |
| **Isolate（隔离）** | 一个上下文装不下所有事 | 拆成多个独立的上下文（Multi-Agent） |
| **Cache（缓存）** | 重复计算太贵了 | 复用已有的计算结果（KV Cache、Prompt Cache） |

## Offload：把信息搬到上下文之外
> 核心思想：**上下文窗口是昂贵且有限的，但文件系统是廉价且无限的**，把不必要的信息从模型上下文里搬出去

Agent 读了一个 3000 token 的文件，这个结果放在上下文里。到了第 30 轮，这个文件内容大概率已经没用了，但还占着 3000 token。如果把它写到文件系统里，上下文里只留一个引用（文件内容已存到 /tmp/file.txt），需要的时候再读回来，3000 token 就释放了

## Reduce：就地压缩
两种策略：
- Compaction 紧凑化：不改对话结构，只缩小内容。比如把老旧的工具结果替换成一个占位符，或者把工具调用的参数缩短
- Summarization 摘要话：用一段LLM生成的总结文字替换整段对话历史，信息损失更大，但token回收也更多

## Retrieve：按需检索
上下文里没有模型需要的信息，可以从外部取回
🌰：模型按需加载工具定义，如果需要一个工具的完整Schema，通过ToolSearch进行检索

## Isolate：上下文隔离
当一个上下文装不下的时候可以拆分城垛，即Multi-Agent。有两种上下文的隔离模式：
- By Communicating（消息传递）：主Agent给子Agent发送指令，子Agent在完全独立的上下文里完成后只把结果返回给主Agent。主Agent上下文只多了一条指令和一个结果，而不是子Agent的思考过程
- By sharing context（Fork）：子Agent直接复制主Agent的完整上下文，在此基础上工作。子Agent可以拥有完整的历史信息，但token开销翻倍

## Cache：复用计算结果
分为三层：KV Cache（模型推理层，没法控制）、Prompt Cache（API层，ROI最高）、Context Collapse（应用层，可逆折叠）

## 维度优先级
1. 先Offload：能不放进上下文的就不放。工具结果写文件、比较大的输出存磁盘、数据操作使用脚本完成
2. 再Cache：减少重复计算。静态prompt缓存、对话历史前缀匹配
3. 然后Reduce：先Compaction，缩小但保留结构；实在不行再Summarization摘要替换
4. 需要的话Isolate：一个Agent搞不定就拆成多个，每个有自己的上下文
5. 贯穿始终Retrieve：模型需要什么信息就按需取，不要预加载