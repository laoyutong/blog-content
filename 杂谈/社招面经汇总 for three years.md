## 项目经历
> 每个公司都用得到！！！

项目有什么难点
做了什么优化（性能 or 交互）
…………

## 非技术
选择公司的偏向（规模、业务）
为什么想面试/离职
业务开发中怎么成长；回顾过去，怎么样可以发展的更好；对于业务的理解，怎么有助于成长


## 前端基础
es6新特性有什么
箭头函数的this指向
事件循环
BFC
水平垂直居中
http缓存
https
Promise.all的执行顺序
变量提升的打印问题
```js
var a = 1 
function a(){}
console.log(a) // 1
```
prototype的打印问题
```js
function F() {}

Object.prototype.a = () => {
  console.log("a");
};

Function.prototype.b = () => {
  console.log("b");
};

const f = new F();

F.a(); // a
F.b(); // b
f.a(); // a
f.b(); // error
```
输入url发生了什么（经典）
回流重绘
var的for循环问题；如何解决
行内、块级元素的差别
有什么隐藏元素的方法，各自的区别
204状态码是什么
频繁触发304的报警，有什么解决方法

## 框架相关
react更新机制
用过HOC么；hooks能替代hoc么
状态管理库的原理
React hook解决了什么；有什么规则限制
React fiber；怎么实现的异步可更新；有什么高优先级的
React的更新是异步的么
React diff原理（细节抠到多节点diff的索引逻辑）
React 18、19新特性
react组件为什么大写；为什么只能返回一个元素（jsx的规范）


webpack loader和插件的区别
webpack热更新
webpack的构建原理
webpack的Compiler是什么；插件有哪些hook

vite为什么快；原理

## 其他
封装组件的经历（基于组件库的二次封装等）；最复杂的一个组件封装
工程化的优化方式
怎么制定的规范（css、react）；推广有遇到什么问题么
设计模式的了解；发布-订阅是什么
错误监控怎么做的
了解小程序、js bridge、node么
tailwind的使用情况；优劣势
ts体操 lengthOfString<'ABCDE'> => 5
ts 类型守卫、 类型谓词（main(str:any):str is string）的概念
ts怎么在本地跑（tsc等工具）
babel是什么；Polyfill怎么做；有没有对于corejs的工程化实践
Vite esbuild rollup的关系
webpack和rollup的区别；为什么一个偏向应用一个偏向库
AI在工作中的应用
虚拟列表的原理
尝试的新鲜技术（rust、webrtc、vite?）
动态加载考虑过用es module的形式么（原本用eval来加载cjs）

## 手撕大法
手写myConst：myConst('a',123)，可以通过console.log(a)得到123，需要区分全局作用于还是函数作用域（Object.defineProperty）
手写runTask：异步执行，尽可能在微任务里执行（如果没有Promise的兜底？）
基于MyComonent封装一个MyCard，新增一个title属性，其他属性都透传（感觉想问vue版本）
写一个hook：返回time和start，start开始倒计时，组件销毁时也停止（注意闭包）
异步并发，有并发上限（高频！！！），都大差不差
```js
const main = (promiseFn, limit) => {
  const arr = [];
  let index = 0;
  return (...args) => {
    const handle = (resolvePlus) => {
      index++;
      promiseFn(...args).then((res) => {
        index--;
        if (arr.length) {
          arr.shift()();
        }
        resolvePlus(res);
      });
    };

    return new Promise((resolve) => {
      if (index < limit) {
        handle(resolve);
      } else {
        arr.push(() => handle(resolve));
      }
    });
  };
}

const getBlog = (i) => { }

const getLimitBlog = main(getBlog, 10)

for (let i = 0; i < 10000; i++) {
  // 并发执行10个
  getLimitBlog(i).then(blog => {

  })
}
```
EventBus
bind + 继承
React useEvent的实现
基于fetch封装，并发限制、根据优先级发请求
React 实现useObserable

两个数组求交集：[[0, 2], [5, 10], [13, 23], [24, 25]] + [[1, 5], [8, 12], [15, 24], [25, 28]] =>  [[1,2],[5,5],[8,10],[15,23],[24,24],[25,25]]
判断字符串是否是回文字符串：'aa', 'aba' => true 'abc' => false
一个字符串删掉一个字符仍是回文字符串： 'aa', 'aabbaca', 'abca' => true 'abc' => false
括号匹配
二叉树上节点的值是否可以构成特定值