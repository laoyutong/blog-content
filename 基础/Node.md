## 基础概念
Node.js是一个运行时环境，基于V8引擎，采用事件驱动、非阻塞式I/0的模型
I/O密集型指的是大部分时间在等待外部响应，而不是消耗CPU计算的操作：网络请求、数据库查询、文件系统操作等

## 事件循环机制
- 初始化阶段
1. Node执行所有同步JS代码
2. 注册setTimeout、fs.readFile等回调
3. 清空同步代码后，启动循环

- 循环顺序
1. timer 定时器阶段
执行setTimeout、setInterval回调
2. pending callbacks
处理延迟的I/O回调，如TCP连接报错
3. Idle,Prepare
内部使用
4. poll 轮询阶段
检索新的I/O事件，如果有任务，立即处理；如果没有则挂起等待
5. check
专门给setImmediate准备的窗口，用于防止饥饿，可以在I/O周期结束后立即执行
6. Close Callbacks
处理关闭的回调，如socket.on('close',……)

- 微任务
在当前阶段完成后立即执行
优先级：process.nextTick > Promise > 其他微任务 > 事件循环阶段

## 框架选型

- Express：回调函数+线性中间件；大而全，自带路由、静态文件服务、模板引擎集成等

- Koa：
  - Promise+洋葱模型
  - 每个请求会创建一个新的context：Koa封装的请求/响应对象、Node原生的HTTP Request/Response、state用于中间件之间传递数据的命名空间、属性代理
  - 通过赋值的方式处理响应
  ```js
  app.use(async (ctx, next) => {
    const name = ctx.query.name; // 代理自 request
    ctx.body = `Hello ${name}`;  // 代理自 response，自动设置状态码 200
  });
  ```

- Fastify：高性能
  - Schema驱动的优化架构：预编译生成优化的序列化函数，性能优于JSON.stringfy
  - 极致的路由算法：find-my-way的高性能路由库，基于Radix Tree基数树的数据结构，路由数量不影响性能
  - …………

- Egg：基于Koa异步编程模型封装，约定优于配置

## Nest
基于TypeScript的模块化驱动 + 依赖注入(Dependency Injection) + 面向切面编程(AOP)

### 模块系统
使用Module作为组织代码的最基本单位
- 实现高内聚和边界清晰
- 依赖注入容器的载体
- 支持全局模块（全局通用的工具模块，如Config、Logger）、动态模块（数据库连接）

### AOP处理链路
解决 代码解耦 和 关注点分离 的问题
1. Middleware：用于处理最通用的逻辑，如解析Body
2. Guards：决定请求是否允许通过
3. Interceptors：在函数执行前转换数据或绑定逻辑（统计接口耗时）
4. Pipes：数据转换或验证
5. Controller：业务逻辑的入口
6. Service：具体的业务实现
7. Interceptors：返回响应前，统一包装返回格式
8. Exception Filters：捕获全局错误并返回标准化的错误响应

### 依赖注入
解决的问题：
- 减少硬编码耦合，代码更整洁：class无需负责实例化所需要的依赖项
- 生命周期管理：Nest负责单例/请求作用域实例的创建、缓存和销毁，无需开发者手动维护全局变量
- 依赖链路

核心角色：
1. 提供者Provider
任何被`@Injectable`装饰的class
2. 消费者Consumer
通常是Controller或另一个Service，通过构造函数注入来申明所需的依赖
```js
@Controller('users')
export class UsersController {
  // 仅需在此声明类型，Nest 就会自动注入实例
  constructor(private readonly usersService: UsersService) {}
}
```
3. 注册地 Module
在Module的providers里注册
```js
@Module({
  controllers: [UsersController],
  providers: [UsersService], // 在这里告诉容器如何实例化 UsersService
})
export class UsersModule {}
```

工作原理：
调用NestFactory.create(AppModule)时开始工作
1. 编译阶段
递归扫描所有Module，识别`@Injectable`、`@Controller`等装饰器
TS启用emitDecoratorMetadata，在编译时生成`design:paramtypes`元数据
利用reflect-metadata在运行时读取元数据就可以知道这个构造函数需要哪些类的实例
2. 构建依赖图
基于反射结果，构建一张有向无环图
循环依赖检测，会检查是否有forwardRef，若果没有则会抛出循环依赖错误
3. 实例化
单例检查，对每一个Provider检查容器内部的Instance Loader是否已经存在该实例
创建实例：如果缓存中没有，根据依赖图递归地调用new
4. 注入阶段
构造函数注入：将准备好的实例作为参数传给constructor
属性注入：class里使用了@Inject装饰属性，会在class实例化之后，手动将对应的实例赋值给这些属性
作用域处理：
- DEFAULT：应用启动时实例化（单例）
- REQUEST：每个进入的请求都会创建一个新实例，并在请求结束后销毁；用于隔离请求数据的场景
- TRANSIENT：每次注入都会创建一个全新的实例；适用无状态的工具类服务