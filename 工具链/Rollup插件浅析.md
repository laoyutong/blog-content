## 构建钩子

### options

| `(options: InputOptions) => InputOptions | null`

可以修改配置选项，如果返回 `null` 则不作任何更改

```jsx
// rollup.config.js
import plugin from "./plugin";

export default {
  input: "./src/index.js",
  output: {
    file: "./output/dist.js",
  },
  plugins: [plugin()],
};

// plugin.js: 修改输出文件地址
export default () => {
  return {
    name: "plugin",
    options(options) {
      options.output[0].file = "./output/updated.js";
      return options;
    },
  };
};
```

这是唯一一个在 `rollup` 配置完全之前执行的钩子，无法访问大部分 `plugin context` 的工具方法

```jsx
options(options) {
    console.log("plugin context:::", this);
},

// plugin context::: { meta: { rollupVersion: '2.70.1', watchMode: false } }
```

### buildStart

> `(options: InputOptions) => void`
> 

在每次构建时会执行，参数中的选项已经被 `options` 钩子转化且添加上了默认值

推荐在这个钩子中进行对配置选项的读取操作

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    buildStart(options) {
      console.log("options:::", options);
    },
  };
};

// terminal
options::: {
  acorn: {
    allowAwaitOutsideFunction: true,
    ecmaVersion: 'latest',
    preserveParens: false,
    sourceType: 'module'
  },
  acornInjectPlugins: [],
  context: 'undefined',
  experimentalCacheExpiry: 10,
  external: [Function (anonymous)],
  inlineDynamicImports: undefined,
  input: [ './src/index.js' ],
  makeAbsoluteExternalsRelative: true,
  manualChunks: undefined,
  maxParallelFileReads: 20,
  moduleContext: [Function (anonymous)],
  onwarn: [Function (anonymous)],
  perf: false,
  plugins: [
    { name: 'plugin', buildStart: [Function: buildStart] },
    {
      load: [Function: load],
      name: 'stdin',
      resolveId: [Function: resolveId]
    }
  ],
  preserveEntrySignatures: 'strict',
  preserveModules: undefined,
  preserveSymlinks: false,
  shimMissingExports: false,
  strictDeprecations: false,
  treeshake: {
    annotations: true,
    correctVarValueBeforeDeclaration: false,
    moduleSideEffects: [Function (anonymous)],
    propertyReadSideEffects: true,
    tryCatchDeoptimization: true,
    unknownGlobalSideEffects: true
  }
}
```

### resolveId

> `(source: string, importer: string | undefined, options: {isEntry: boolean, custom?: {[plugin: string]: any}) => string | false | null | {id: string, external?: boolean | "relative" | "absolute", moduleSideEffects?: boolean | "no-treeshake" | null, syntheticNamedExports?: boolean | string | null, meta?: {[plugin: string]: any} | null}`
> 

可以自定义解析器， `source` 就是引入的文件路径, `importer` 是被解析过后的绝对路径，如果是入口文件则 `importer` 就是 `undefined`

```jsx
// rollup.config.js
export default () => {
  return {
    name: "plugin",
    resolveId(source, importer) {
      console.log("resolveId:::", source, importer);
      return null;
    },
  };
};

// index.js
import name from "./name";
console.log(name);

// ./name.js
const name = "name";
export default name;

// terminal
resolveId::: ./src/index.js undefined
resolveId::: ./name /Users/Desktop/rollup-demo/src/index.js
```

返回 `null` 会推迟给其他的 `resolveId` 执行，最终返回默认的解析行为

可以在 `resolveId` 的下一个钩子 `load` 中看到解析结果

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    resolveId(source, importer) {
      console.log("resolveId:::", source, importer);
      return null;
    },
    load(id) {
      console.log("load:::", id);
      return null;
    },
  };
};

// terminal: 相对路径被解析成了绝对路径
resolveId::: ./src/index.js undefined
load::: /Users/Desktop/rollup-demo/src/index.js
resolveId::: ./name /Users/Desktop/rollup-demo/src/index.js
load::: /Users/Desktop/rollup-demo/src/name.js
```

返回 `false` 表示 `source` 会作为一个外部模块而不被包括在构建产物中

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    resolveId(source, importer) {
      if (source === "./name") {
        return false;
      }
			return null
    },
  };
};

// output/dist.js
import name from './name';

console.log(name);
```

返回一个对象的时候可以将一个导入解析成一个不同的 `id` ，同时排除在构建产物之外

可以使用外部依赖来替换依赖而不需要使用 `external` 选项来配置

如果设置 `external` 为 `true` 则会根据用户设置的 `makeAbsoluteExternalRelative` 选项

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    resolveId(source) {
      if (source === "lodash") {
        return { id: "lodash-es", external: true };
      }
      return null;
    },
  };
};

// index.js
import { isEmpty } from "lodash";
console.log(isEmpty({}));

// output/dist.js
import { isEmpty } from 'lodash-es';
console.log(isEmpty({}));
```

如果 `moduleSideEffects` 返回 `no-treeshake` ，则该模块会关闭 `treeshaking`功能

如果返回 `null` 或者不返回 `moduleSideEffects`该字段，则会由 `treeshake.moduleSideEffects` 选项决定或者默认为 `true`

`load` 和 `transform` 钩子中都可以覆盖该设置

```jsx
// plugin.js
import path from 'path'
export default () => {
  return {
    name: "plugin",
    resolveId(source) {
      if (source === "./name.js") {
        return {
          id: path.resolve(__dirname, "src", source),
          moduleSideEffects: "no-treeshake",
        };
      }
      return null;
    },
  };
};

// index.js
import { name } from "./name.js";
console.log(name);

// name.js
export const name = "name";
export const age = 18;

// output/dist.js
const name = "name";
const age = 18;

console.log(name);
```

如果 `moduleSideEffects` 设置成 `false` ，当其他模块没有从这个模块导入任何东西的时候，这个模块即使有副作用也不会被包含

```jsx
// index.js
import { name } from "./window.js";
console.log("index");

// window.js
export const name = "name";
window.abc = "abc";

// output/dist.js 
// 当 moduleSideEffects 设置成false的时候
console.log("index");

// 当 moduleSideEffects 设置成true的时候
window.abc = "abc";
console.log("index");
```

### load

> `(id: string) => string | null | {code: string, map?: string | SourceMap, ast? : ESTree.Program, moduleSideEffects?: boolean | "no-treeshake" | null, syntheticNamedExports?: boolean | string | null, meta?: {[plugin: string]: any} | null}`
> 

自定义加载器，如果返回 `null` 则推迟给其他加载函数，最终就默认是从文件系统加载

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    resolveId(source) {
      if (source === "name") {
        return source;
      }
      return null;
    },
    load(id) {
      if (id === "name") {
        return "export const name = 'name';";
      }
			return null
    },
  };
};

// index.js
import { name } from "name";
console.log("name:::", name);

// output/dist.js
const name = "name";

console.log("name:::", name);
```

对于已经在钩子里使用了 `this.parse` 生成了 `AST` 的场景，为了防止额外的解析开销，可以返回一个包含 `code` 、 `ast` 、 `map` 的对象。这个 `ast` 必须是标准的 `ESTree AST` ，每个节点都包含 `start` 和 `end` 属性。如果转换时没有移动代码位置，可以设置 `map` 为 `null` 来保持现有的 `sourcemaps`

### transform

> `(code: string, id: string) => string | null | {code?: string, map?: string | SourceMap, ast? : ESTree.Program, moduleSideEffects?: boolean | "no-treeshake" | null, syntheticNamedExports?: boolean | string | null, meta?: {[plugin: string]: any} | null}`
> 

用于转换单个模块，和 `load` 类似，也可以返回一个带有 `code` 、 `ast`、 `map` 的对象，用于已经生成 `AST` 的场景

```jsx
// plugin.js
import { transformAsync } from "@babel/core";
export default () => {
  return {
    name: "plugin",
    async transform(code) {
      return await transformAsync(code, {
        presets: ["@babel/preset-env"],
      });
    },
  };
};

// index.js
const add = (a, b) => a + b;
console.log(add(1, 2));

// output/dist.js
var add = function add(a, b) {
  return a + b;
};

console.log(add(1, 2));
```

## 插件上下文

### this.parse

> `(code: string, acornOptions?: AcornOptions) => ESTree.Program`
> 

使用 `rollup` 内置的 `acorn` 来将代码转换成 `AST`

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    transform(code) {
      console.log(this.parse(code));
      return code;
    },
  };
};

// index.js
const name = "name";
console.log("name:::", name);

// terminal
Node {
  type: 'Program',
  start: 0,
  end: 51,
  body: [
    Node {
      type: 'VariableDeclaration',
      start: 0,
      end: 20,
      declarations: [
        Node {
          type: 'VariableDeclarator',
          start: 6,
          end: 19,
          id: Node { type: 'Identifier', start: 6, end: 10, name: 'name' },
          init: Node {
            type: 'Literal',
            start: 13,
            end: 19,
            value: 'name',
            raw: '"name"'
          }
        }
      ],
      kind: 'const'
    },
    Node {
      type: 'ExpressionStatement',
      start: 21,
      end: 50,
      expression: Node {
        type: 'CallExpression',
        start: 21,
        end: 49,
        callee: Node {
          type: 'MemberExpression',
          start: 21,
          end: 32,
          object: Node {
            type: 'Identifier',
            start: 21,
            end: 28,
            name: 'console'
          },
          property: Node { type: 'Identifier', start: 29, end: 32, name: 'log' },
          computed: false,
          optional: false
        },
        arguments: [
          Node {
            type: 'Literal',
            start: 33,
            end: 42,
            value: 'name:::',
            raw: '"name:::"'
          },
          Node { type: 'Identifier', start: 44, end: 48, name: 'name' }
        ],
        optional: false
      }
    }
  ],
  sourceType: 'module'
}
```

### this.getModuleInfo

> `(moduleId: string) => (ModuleInfo | null)`
> 

返回模块的额外信息，在 `buildEnd` 钩子之前是有可能发生变化的

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    load(id) {
      console.log(this.getModuleInfo(id));
      return null;
    },
  };
};

// index.js
const name = "name";
console.log("name:::", name);

// terminal
{
  ast: null,
  code: null,
  dynamicallyImportedIdResolutions: [Getter],
  dynamicallyImportedIds: [Getter],
  dynamicImporters: [Getter],
  hasDefaultExport: [Getter],
  id: '/Users/Desktop/rollup-demo/src/index.js',
  implicitlyLoadedAfterOneOf: [Getter],
  implicitlyLoadedBefore: [Getter],
  importedIdResolutions: [Getter],
  importedIds: [Getter],
  importers: [Getter],
  isEntry: true,
  isExternal: false,
  isIncluded: [Getter],
  meta: {},
  moduleSideEffects: true,
  syntheticNamedExports: false
}
```

### this.resolve

> `(source: string, importer?: string, options?: {skipSelf?: boolean, isEntry?: boolean, isEntry?: boolean, custom?: {[plugin: string]: any}}) => Promise<{id: string, external: boolean | "absolute", moduleSideEffects: boolean | 'no-treeshake', syntheticNamedExports: boolean | string, meta: {[plugin: string]: any}} | null>`
> 

使用和 `rollup` 相同的插件来解析导入为模块 `id` ，在其他的钩子里调用 `this.resolve` 会触发 `resolveId` 钩子的执行

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    resolveId(source, importer) {
      console.log("resolveId", source, importer);
      return null;
    },
    load() {
      this.resolve("./test", undefined);
      return null;
    },
  };
};

// index.js
console.log("no importer");

// terminal
resolveId ./src/index.js undefined
resolveId ./test undefined
```

可以用于确认一个导入是否是 `external` 的

```jsx
// rollup.config.js
import plugin from "./plugin";

export default {
  input: "./src/index.js",
  output: {
    file: "./output/dist.js",
  },
  plugins: [plugin()],
  external: ["./name"],
};

// plugin.js
export default () => {
  return {
    name: "plugin",
    load() {
      this.resolve("./name").then((res) => {
        console.log("result:::", res);
      });
      return null;
    },
  };
};

// index.js
import { name } from "./name";
console.log(name);

// terminal
result::: {
  external: true,
  id: '/Users/Desktop/rollup-demo/name',
  meta: {},
  moduleSideEffects: true,
  syntheticNamedExports: false
}
```

如果返回了 `null` 表示这个导入没有被 `rollup` 和任何插件解析且没有被用户标明是 `external`

```jsx
// rollup.config.js
import plugin from "./plugin";

export default {
  input: "./src/index.js",
  output: {
    file: "./output/dist.js",
  },
  plugins: [plugin()]
};

// plugin.js
export default () => {
  return {
    name: "plugin",
    load() {
      this.resolve("./name").then((res) => {
        console.log("result:::", res);
      });
      return null;
    },
  };
};

// index.js
console.log("no import");

// terminal
result::: null
```

如果设置 `skipSelf` 为 `true` ，则在解析的时候会跳过调用 `this.resolve` 的`resolveId` 钩子

在如下的例子中，如果没有 `skipSelf` 则会陷入死循环

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    resolveId(source, importer) {
      console.log("resolveId");
      return this.resolve(source, importer, { skipSelf: true }).then(
        (res) => res.id
      );
    },
  };
};
```

### this.load

> `({id: string, moduleSideEffects?: boolean | 'no-treeshake' | null, syntheticNamedExports?: boolean | string | null, meta?: {[plugin: string]: any} | null, resolveDependencies?: boolean}) => Promise<ModuleInfo>`
> 

通过 `id` 来加载并解析模块

如果 `this.resolve` 的返回值不是 `null` 或者是 `external`的，可以直接将其当做参数来传递

```jsx
// plugin.js
export default () => {
  return {
    name: "plugin",
    async resolveId(source, importer) {
      const resolution = await this.resolve(source, importer, {
        skipSelf: true,
      });
      const moduleInfo = await this.load(resolution);
      console.log(moduleInfo);
      return null;
    },
    load() {
      return null;
    },
  };
};
// index.js
console.log("no importer");

// terminal
{
  ast: Node {
    type: 'Program',
    start: 0,
    end: 28,
    body: [ [Node] ],
    sourceType: 'module'
  },
  code: 'console.log("no importer");\n',
  dynamicallyImportedIdResolutions: [Getter],
  dynamicallyImportedIds: [Getter],
  dynamicImporters: [Getter],
  hasDefaultExport: [Getter],
  id: '/Users/Desktop/rollup-demo/src/index.js',
  implicitlyLoadedAfterOneOf: [Getter],
  implicitlyLoadedBefore: [Getter],
  importedIdResolutions: [Getter],
  importedIds: [Getter],
  importers: [Getter],
  isEntry: false,
  isExternal: false,
  isIncluded: [Getter],
  meta: {},
  moduleSideEffects: true,
  syntheticNamedExports: false
}
```

如果该模块已经被加载， `this.load` 只是等其加载完成后返回模块信息

如果该模块还没有被其他模块导入，不会自动触发加载这个模块导入的其他模块，相反只有这个模块被实际导入后，才会加载其依赖

```jsx
// plugin.js
import path from "path";
export default () => {
  return {
    name: "plugin",
    async resolveId() {
      const resolution = await this.resolve(
        "./name.js",
        path.resolve(__dirname, "src", "./index.js"),
        {
          skipSelf: true,
        }
      );
      await this.load(resolution);
      return null;
    },
    load(id) {
      console.log("id", id);
      return null;
    },
  };
};

// index.js
import { name } from "./name.js";
console.log("name:::", name);

// name.js
import { age } from "./age.js";
export const name = "name";
console.log("age:::", age);

// age.js
export const age = "age";

// terminal
id /Users/Desktop/rollup-demo/src/name.js
id /Users/Desktop/rollup-demo/src/index.js
id /Users/Desktop/rollup-demo/src/age.js
```

`this.load` 如果设置 `resolveDependencies`，会等该模块所有的依赖 `id` 都被解析后才返回 `Promsie` 的结果

```jsx
// plugin.js
import path from "path";
export default () => {
  return {
    name: "plugin",
    async resolveId(source, importer) {
      console.log(source, importer);
      if (!importer) {
        await this.load({
          id: path.resolve(__dirname, "src", "age.js"),
          resolveDependencies: true,
        }).then((res) => {
          console.log("age load");
        });
      }
      return null;
    },
  };
};

// index.js
import { name } from "./name.js";
import { age } from "./age.js";
console.log(age, name);

// name.js
export const name = "name";

// age.js
import { work } from "./work";
export const age = "age";
console.log(work);

// terminal
./src/index.js undefined
./work /Users/Desktop/rollup-demo/src/age.js
age load
./name.js /Users/Desktop/rollup-demo/src/index.js
./age.js /Users/Desktop/rollup-demo/src/index.js
```

## 插件工具包

****`@rollup/pluginutils`**** : 插件常用的工具方法

### ****createFilter****

传入 `include` 和 `exclude` 来得到一个筛选方法，用于确定是否需要操作某些模块

```jsx
import { createFilter } from '@rollup/pluginutils';

export default function plugin(options = {}) {
 const filter = createFilter(options.include, options.exclude});
  return {
    transform(code, id) {
      if (!filter(id)) return;
      // proceed with the transformation...
    }
  };
}
```

### normalizePath

可以将路径分隔符转换成正斜杠

```jsx
import { normalizePath } from '@rollup/pluginutils';

normalizePath('foo\\bar'); // 'foo/bar'
normalizePath('foo/bar'); // 'foo/bar'
```

### addExtension

如果 `id` 没有文件拓展名则进行添加，默认是 `.js`
```js
import { addExtension } from '@rollup/pluginutils';

export default function plugin(options = {}) {
  return {
    resolveId(code, id) {
      id = addExtension(id); // `foo` -> `foo.js`, `foo.js` -> `foo.js`
      id = addExtension(id, '.myext'); // `foo` -> `foo.myext`, `foo.js` -> `foo.js`
    }
  };
}
```