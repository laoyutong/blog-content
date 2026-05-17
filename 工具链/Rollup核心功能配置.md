## external

> `(string | RegExp)[] | RegExp | string | (id: string, parentId: string, isResolved: boolean) => boolean`
> 

可以传入字符串、正则，或者一个返回 `boolean` 的方法，参数为模块的 `id` 、执行导入的模块 `id` ，以及该 `id` 是否已经被解析

```jsx
import path from 'path';
export default {
  external: [
    'some-externally-required-library',
    path.resolve( __dirname, 'src/some-local-file-that-should-not-be-bundled.js' ),
    /node_modules/
  ]
};
```

会将相应的文件保留在打包之外。如果想排除第三方库的内容，需要借助 `@rollup/plugin-node-resolve`等插件

```jsx
// input:
import a from "./a";
console.log(a);

// output: without external
const a = 123;
console.log(a);

// output: with external: [path.resolve(__dirname, "src/a.js")],
import a from './a.js';
console.log(a);
```

如果是 `iife` 或 `umd` 的打包格式，需要通过 `output.globals` 等选项来提供全局变量名称来替换外部导入

```jsx
import resolve from "@rollup/plugin-node-resolve";

export default {
  input: "./src/index.js",
  output: {
    file: "./dist/index.js",
    format: "iife",
    globals: {
      "lodash-es": "test",
    },
  },
  plugins: [resolve()],
  external: ["lodash-es"],
};

// input:
import { isEmpty } from "lodash-es";
console.log(isEmpty({}));

// output:
(function (lodashEs) {
	'use strict';
	console.log(lodashEs.isEmpty({}));
})(test);
```

## input

> `string | string [] | { [entryName: string]: string }`
> 

打包的入口文件。如果是一个数组或者对象，会打包到分别的输出 `chunk` 中

如果没有填写 `output.file` ，会依据 `output.entryFileNames` 来生成 `chunk` 名字

如果是对象形式， 输出文件名的 `[name]` 部分是对象属性的名称

```jsx
export default {
  input: {
    a: 'src/a.js',
    b: 'src/b.js'
  },
  output: {
    entryFileNames: 'entry-[name].js' // entry-a.js entry-b.js
  }
};
```

而对于数组形式的话，则是入口的文件名

```jsx
export default {
  input: ["./src/a.js", "./src/b.js"],
  output: {
    entryFileNames: "entry-[name].js", // entry-a.js entry-b.js
  },
};
```

## output.dir

> `string`
> 

指定生成 `chunk` 的目录。在生成多个 `chunk` 的时候使用，否则使用 `file` 选项即可

## output.file

> `string`
> 

输出的文件，在适用的时候也可以生成 `sourcemap` ，只能在生成不大于一个 `chunk` 的时候使用

## output.format

> `string = "es"`
> 

打包文件的生成格式，包括

- amd： `Asynchronous Module Definitioe`，现在使用较少
- cjs： `CommonJS` ，可以运行在 `Node`
- es：`ES module`，可以通过 `<script type="module">` 运行在现代浏览器里
- iife： 立即执行函数，可以直接在 `<script>` 里执行
- umd：通用的模块定义，支持多种引入方式
- system： `SystemJS` 加载器的原生格式

## output.globals

> `{ [id: string]: string } | ((id: string) => string)`
> 

在 `umd`、`iife`的产物中使用了 `external imports` ，必须使用该选项来指定相应的名称

例：在项目中 `import $ from 'jquery'`，配置文件中把`jquery`放入到`external`里

```jsx
// rollup.config.js
export default {
  external: ['jquery'],
  output: {
    format: 'iife',
    name: 'MyBundle',
    globals: {
      jquery: '$'
    }
  }
};

// output:
var MyBundle = (function ($) {
  // ...
}($));
```

## output.name

> `string`
> 

对于 `iife` 、 `umd` 的输出格式需要指定全局变量名，这样其他的 `scripts` 就可以通过该变量名称来访问该包的导出内容

```jsx
// rollup.config.js
export default {
  ...,
  output: {
    file: 'bundle.js',
    format: 'iife',
    name: 'MyBundle'
  }
};

// output:
var MyBundle = (function () {...})
```

## output.plugins

> `OutputPlugin | (OutputPlugin | void)[]`
> 

针对该`output`添加插件，且不是每个插件都可以使用，仅限于使用在 `bundle.gengerate` 或 `bundle.write` 期间运行的钩子的插件，即在 `rollup` 完成主要分析之后

```jsx
import { terser } from 'rollup-plugin-terser';

export default {
  input: 'main.js',
  output: [
    {
      file: 'bundle.js',
      format: 'es'
    },
    {
      file: 'bundle.min.js',
      format: 'es',
      plugins: [terser()]
    }
  ]
};
```

## plugins

> `Plugin | (Plugin | void)[]`
> 

注册插件，如果是 `falsy` 的插件会直接被忽略

```jsx
import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';

const isProduction = process.env.NODE_ENV === 'production';

export default (async () => ({
  input: 'main.js',
  plugins: [resolve(), commonjs(), isProduction && (await import('rollup-plugin-terser')).terser()],
  output: {
    file: 'bundle.js',
    format: 'cjs'
  }
}))();
```
