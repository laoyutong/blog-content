## 编译流程

### 核心概念
- complier：Webpack的运行环境，负责启动构建、监听文件变化、输出资源以及结束编译
- compilation：是一次具体的构建过程，负责构建依赖图、管理资源状态等；每次文件变更触发重新编译都会创建一个新的

### 主体流程
1. 读取参数：从配置文件和Shell命令中读取，得出最终的配置对象
2. 创建Compiler对象：实例化一个全局唯一的对象，包含完整的Webpack环境配置
3. 执行用户配置插件的apply、加载各种内置插件
4. 执行compiler的run开始编译流程，创建Compilation对象，根据entry找出所有的入口模块，调用loader转译对应的模块，调用Acorn将代码转换成AST，递归遍历AST得到完整的模块依赖关系图
5. 根据入口和模块的依赖关系，组装成一个个包含多个模块的Chunk，再把每个Chunk转换成单独的文件加入到输出列表
6. 根据配置确定输出的路径和文件名，写入到文件系统

## 热更新

1. 使用webpack-dev-server托管静态资源，以runtime的方式注入HMR客户端代码
2. 浏览器加载页面后，和server建立websocket连接
3. webpack监听到文件变化后，增量构建发生变化的模块，通过websocket发送hash事件
4. 浏览器接收到hash文件后，请求manifest资源文件，确认增量变更范围，哪些chunk发生了变化
5. 浏览器加载发生变更的增量模块
6. webpack运行时触发变更模块的module.hot.accept回调，执行代码变更逻辑

## loader & plugin
 loader：模块内容的**转化器**
- 使用方式：在`module.rules`配置
- 特性：支持链性调用，如处理Less：less-loader => css-loader => style-loader
- 时机：在模块编译阶段运行

plugins：构建流程的**拓展器**，通过Tapable Hooks机制
- 使用方式：在`plugins`里实例化
- 时机：在构建的各个生命周期中注入自定义逻辑

常见hooks：
compiler.hooks.compilation：创建compilation对象后触发
compiler.hooks.make：开始构建时触发
compiler.hooks.emit：输出asset到output目录之前执行
compiler.hooks.done：在compilation完成时执行

compilation.hooks.buildModule：模块构建之前触发，可以修改模块
compilation.hooks.processAssets：修改产物内容，代码压缩、生成清单

## 模块联邦
实现运行时的代码共享，可以动态地加载并运行一个应用的代码

核心角色：
每个应用既可以是提供者，也可以是消费者
- Host 宿主方：消费方，负责加载并集成远程模块的应用
- Remote 远程方：提供方，负责暴露自己的组件、函数等供其他应用使用

优势：
- 按需加载：只有用到远程组件时才会去下载
- 版本实时更新：远程项目部署，宿主端无需重新构建，刷新页面即可生效；无需像NPM包一样，每次改动都需要重新发布、宿主环境重新安装后再构建部署
- 依赖共享：如果两个项目都用了React，宿主端可配置只下载一份，避免重复加载

工作原理：
1. 加载入口
当Host启动时，会加载Remote提供的removeEntry.js，包含异步获取具体模块和初始化共享依赖池的方法
2. 初始化Shared Scope
Host和Remote会共同维护一个共享作用域，Host会把自己的共享库信息传给Remote
双方协商版本，如果Host已经加载了符合要求的版本，Remote就会直接复用Host的内存实例，而不是重新下载
3. 异步请求模块
执行到import remote模块时，Webpack会查找remoteEntry的映射表，动态加载对应的Chunk，并将其注入到当前应用的运行环境中
