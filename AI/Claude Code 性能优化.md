## 并行预取
启动子进程，和import链并行执行
- startMdmRawRead：并行调用execFile来获取plist配置，满足企业级合规要求
- startKeychainPrefetch：并行获取oAuth、legacy两个keychain，读取有效的会话token或认证信息

## 延迟加载
- 懒加载
通过getter + require()的方式，只有首次需要时才加载
```js
const messageSelector =
  (): typeof import('src/components/MessageSelector.js') =>
    require('src/components/MessageSelector.js')
```
- 惰性schema
避免在模块加载阶段就执行 Zod schema 构建，只在首次被实际使用时才构建
```js
export function lazySchema<T>(factory: () => T): () => T {
  let cached: T | undefined
  return () => (cached ??= factory())
}

const attachmentSchema = lazySchema(() =>
  z.object({
    file_uuid: z.string(),
    file_name: z.string(),
  }),
)
```
- Feature Flags通过配置来控制某个功能可用，如果没有开启，Bun 会直接在打包阶段删掉这段逻辑（Dead Code Elimination）
```js
import { feature } from 'bun:bundle'
const proactive =
  feature('PROACTIVE') || feature('KAIROS')
    ? require('./commands/proactive.js').default
    : null
```