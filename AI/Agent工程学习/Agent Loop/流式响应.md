## 流式响应选型
SSE：Server-Sent Events 服务端发送事件，服务端往客户端推数据，客户端只管接收

优势：
- 跑在标准HTTP上：不需要协议升级和特殊的负载均衡配置等内容，成本极低
- 重连友好：定义了Last-Event-ID和重试机制，断了之后重连有据可循

## 模型流式输出格式
模型是自回归生成的——一个 token 一个 token 往外蹦，API 把这个过程包装成了一系列 SSE 事件
```
1. message_start        → 告诉你：一条新消息开始了
2. content_block_start  → 告诉你：一个内容块开始了（文本块 or 工具调用块）
3. content_block_delta  → 一个个 token 推过来："你" "好" "，" "我" "来" ...
4. content_block_delta  → 继续推...
5. content_block_stop   → 告诉你：这个内容块结束了
6. message_delta        → 告诉你：整条消息的元信息（为什么停了、用了多少 token）
7. message_stop         → 告诉你：整条消息结束了
```
可以使用流式文本的分段推送，设一个缓存区，攒够一定量文字后推出去
- 优先找段落便捷，比如两个换行
- 没有段落就找句号
- …………
- 设置字符上限，超了就强制切；如果有代码块，就先把代码关上，下一段再重新打开，保证两段内容都能正常渲染

## Tool Call流式解析
模型决定调用一个工具时，会输出一个tool_use类型的内容，包含工具名和参数
收到的SSE事件流：
```
content_block_start  → {"type": "tool_use", "name": "read_file", "input": {}}

content_block_delta  → partial_json: '{"file_'
content_block_delta  → partial_json: 'path": "'
content_block_delta  → partial_json: 'src/uti'
content_block_delta  → partial_json: 'ls.ts"}'

content_block_stop   → （这个工具块结束了）
```
需要等到 content_block_stop 事件到来时，才能拼成完整的 {"file_path": "src/utils.ts"}，然后 JSON.parse() 解析

## 工具执行方式
最简单的方式：等模型整个消息说完后再依次执行工具，但整体耗时较长，可以优化成工具块一完成就立刻开始执行
但是需要依赖工具的具体类型：
- Read：只读不写，多个Read可以并发跑
- Glob/Grep：只搜索，不修改，可以并发
- Edit：写操作，必须独占执行，等前面所有的工具都完成了再执行，且执行期间不跑其它工具
- Bash：看具体命令，ls安全，但rm不是

在安全和性能之间找平衡：能并发的尽量并发，不能并发的坚决串行