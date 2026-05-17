## 是啥
tailwindcss本质上是一个postcss插件，在它的规则下写类名就可以自动生成相应的样式，简单来说就是提供了一堆开箱即用的原子化类名。
- 开发中的index.tsx
```js
<div className="flex justify-between items-center">
```
- 打包后的index.css
```css
.flex {
  display: flex;
}
.items-center {
  align-items: center;
}
.justify-between {
  justify-content: space-between;
}
```
## 为啥要用
### 更小的构建体积
一个dom元素对应一个类名的样式编写方式，会造成很多的重复样式代码。
如下🌰：在打包后的样式产物里，display: flex会出现两次。
```css
.a {
  display: flex;
  justify-content: space-between;
}

.b {
  display: flex;
  justify-content: space-around;
}
```
但是通过原子化的样式编写方式，只会出现三个原子类名。
即使在100个地方使用了display:flex，最终的产物里也只会有flex这一个类名。
```css
.flex {
  display: flex;
}
.justify-between {
  justify-content: space-between;
}
.justify-around {
  justify-content: space-around;
}
```
为了解决样式冲突而使用的嵌套语法+css module的方案，对样式文件的体积也是一种考验。
- index.tsx
```jsx
<div className={style.content}>
  <div className={style.header}>
    <div className={style.left}>
      <div className={style.title}>title</div>
      <div className={style.content}>content</div>
    </div>
    <div className={style.right}> right</div>
  </div>
</div>
```
- style.module.scss
```css
.content {
  .header {
    .left {
      .title {
        display: flex;
      }

      .content {
        color: red;
      }
    }

    .right {
      line-height: 18px;
    }
  }
}
```
- 样式产物
```css
.content___XZmmG .header___yuXTB .left___9v2w5 .title___bIYKs {
  display: flex;
}
.content___XZmmG .header___yuXTB .left___9v2w5 .content___XZmmG {
  color: red;
}
.content___XZmmG .header___yuXTB .right___UQlJn {
  line-height: 0.48rem;
}
```
### 更快的开发/维护效率
- 代码量
首先从编写的代码量上进行论证，一个原子化的类名肯定比它对应的具体样式要简略得多。
特别是一些简单的dom元素场景，只有几个小样式还得纠结下到底用什么类名，而原子化再也不用担心取名问题。
```js
// 原子化CSS方案
<div className="flex justify-between items-center">

<div className="m-4">

// 常规方案
import style from './style.module.scss'

<div className={style.flex} >

<div className={style.margin} >

.margin{
    margin: 16px;
}

.flex{
    display: flex;
    justify-content: space-between;
    align-items: center;
}
```
- 文件切换
无需切换上下文，原子化样式仅在tsx文件中就能完成整个需求的开发。
特别是阅读其他人代码的时候，不仅在tsx和scss之间来回切换，遇到一堆.title、.content的时候还得看它的爸爸是谁，它的爷爷是谁？？？
- 维护成本
css module里html和css的层级结构基本都是一致的，当dom元素需要跨层级的调整时，都得同步更改css文件的格式，特别是删除等操作，基本不会同步删除相应的样式，也不知道这个删了会不会有问题，导致样式文件难以维护；而原子化的样式跟着标签直接走就行了，不需要其他的心智负担。
## 怎么用
### 安装
> https://tailwindcss.com/docs/installation/using-postcss
- 安装依赖
```
npm install -D tailwindcss postcss autoprefixer
```
- 配置postcss.config.js
```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  }
}
```
- 配置tailwind.config.js
```
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
}
```
- 在入口的css文件里添加指令
```
@tailwind base;  // 按需用，就是一堆初始化的样式
@tailwind components;
@tailwind utilities; // 必须要
```
- 下一个Tailwind CSS IntelliSense的vscode的插件，就可以开始愉快的玩耍了
### 基本使用
> 首先打开tailwind的文档，哪里不懂搜哪里，毕竟那么多的样式肯定记不全
> https://tailwindcss.com/docs/installation

直接使用原子化的类名
```jsx
<div className="m-2 flex font-bold rounded">

// output
.m-2 {
  margin: 0.5rem;
}
.flex {
  display: flex;
}
.rounded {
  border-radius: 0.25rem;
}
.font-bold {
  font-weight: 700;
}
```
因为用的是rem，对于一些设置了html的fontSize场景，不太好计算。
对于这种情况可以直接指定其具体值，如：
```jsx
 <div className="text-[#64666B] text-[12px] leading-[18px] pb-[12px]">
```
使用hover等伪类，你用内联样式可以写么？
```jsx
<button class="bg-sky-500 hover:bg-sky-700">
```
甚至可以直接实现媒体查询，你用内联样式可以写么？
```jsx
<img className="w-16 md:w-32 lg:w-48">

// output
.w-16 {
  width: 4rem;
}

@media (min-width: 768px) {
  .md\:w-32 {
    width: 8rem;
  }
}
@media (min-width: 1024px) {
  .lg\:w-48 {
    width: 12rem;
  }
}
```
### 自定义样式
> https://tailwindcss.com/docs/adding-custom-styles#using-css-and-layer

最简单的就是在index.css里直接声明一个类。
```css
.my-custom-style {
  /* ... */
}
```
也可以通过@layer将样式放到tailwind的层次里，自动帮助控制声明顺序，同时可以支持hover:等伪元素。
```css
@layer components {
  .my-custom-style {
    /* ... */
  }
}
```
通过@apply可以在自定义的类名上聚合原子类。
```
<!-- Before extracting a custom class -->
<button className="py-2 px-4 bg-blue-500 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75">
  Save changes
</button>

<!-- After extracting a custom class -->
<button className="btn-primary">
  Save changes
</button>

// index.css
@layer components {
  .btn-primary {
    @apply py-2 px-4 bg-blue-500 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75;
  }
}
```

### 配置文件
> https://tailwindcss.com/docs/configuration

对于颜色等内容，设计基本都有一套固定的规范，蓝色就这么4、5种，可以直接在theme的colors进行配置，文字颜色和背景颜色都可以使用。
也可以在配置文件里覆盖默认的样式。
```jsx
<span className="bg-blue-EB text-blue-33">
```
```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    colors: {
      blue: {
        '2F': '#2F88FF',
        EB: '#EBF3FF',
        33: '#338AFF',
        A1: '#a1caff',
      },
      gray: {
        FA: '#FAFAFA',
        64: '#64666B',
        96: '#969AA0',
        66: '#666',
        E0: '#e0e0e0',
        99: '#999',
        F5: '#F5F5F5',
        FF: '#FFF',
      },
      black: {
        32: '#323335',
        33: '#333',
      },
    },
    fontSize: {
      xs: ['12px', '18px'], // 默认是 12 16
      sm: ['14px', '22px'], // 默认是 14 20
    },
  },
};
```
可以通过plugins来配置插件。
官方的@tailwindcss/aspect-ratio可以添加aspect-w-{n} 和 aspect-h-{n} 类，它们可以组合起来为元素提供固定的纵横比。
```
module.exports = {
  plugins: [
    require('@tailwindcss/aspect-ratio'),
  ],
}

<div class="aspect-w-16 aspect-h-9">
```
其他杂七杂八的配置项
- prefix
添加前缀
```
module.exports = {
  prefix: 'tw-',
}

<div class="tw-text-lg md:tw-text-xl tw-bg-red-500 hover:tw-bg-blue-500">
```
- important
是否标记!important
```
module.exports = {
  important: true,
}

.leading-none {
  line-height: 1 !important;
}
.leading-tight {
  line-height: 1.25 !important;
}
.leading-snug {
  line-height: 1.375 !important;
}
```
- ……