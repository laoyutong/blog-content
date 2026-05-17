## 区分开发和生产环境
在打包的时候，将产物的静态资源路径替换成`cdn`路径前缀
通过`process.env.NODE_ENV`是否是`production`来判断，开发的时候环境变量可能为空，导致开发路径不符合预期
```js
{
    base: process.env.NODE_ENV === "production" ? CDN_URL_PREFIX : "/",
}
```

## cdn插件
不打包`react`这些第三方库，直接通过相应的`cdn`链接来引入
解析需要处理的模块配置，读取其在`node_modules`里的版本，通过`rollup-plugin-external-globals`插件来转换打包代码，然后通过`vite`提供的`transform`钩子插入`script`标签来引入`cdn`资源
```js
import {
  UserConfig,
  PluginOption,
} from "vite";
import externalGlobals from "rollup-plugin-external-globals";

const prodUrl = "https://xxxxxx/:name@:version/:path";

const modules: vitePluginCDNOption["modules"] = [
  {
    name: "react",
    var: "React",
  },
  {
    name: "react-dom",
    var: "ReactDOM",
  },
  {
    name: "history",
    var: "HistoryLibrary",
  },
  {
    name: "react-router",
    var: "ReactRouter",
  },
  {
    name: "react-router-dom",
    var: "ReactRouterDOM",
  },
];

const getVersionInNodeModules = (name, pathToNodeModules = process.cwd()) => {
  const packageJson = "package.json";
  try {
    return require(path.join(
      pathToNodeModules,
      "node_modules",
      name,
      packageJson
    )).version;
  } catch (e) {
    return null;
  }
};

const vitePluginCDN: (option: vitePluginCDNOption) => PluginOption = (
  option: vitePluginCDNOption
) => {
  const { modules, prodUrl } = option;
  return {
    name: "vite-plugin-cdn",
    enforce: "post",
    transformIndexHtml: {
      config: () => {
        const userConfig: UserConfig = {
          build: {
            rollupOptions: {},
          },
        };
        const externalMap = {};
        modules.forEach((module) => {
          externalMap[module.name] = module.var;
        });
        userConfig.build.rollupOptions = {
          plugins: [externalGlobals(externalMap)],
        };
        return userConfig;
      },
      transform: async (html) => {
        return {
          html,
          tags: modules.map(({ name, path }) => {
            const version = getVersionInNodeModules(name);
            return {
              tag: "script",
              attrs: {
                defer: "defer",
                src: prodUrl
                  .replace(":name", name)
                  .replace(":version", version ?? "latest")
                  .replace(":path", path ?? `umd/${name}.production.min.js`),
              },
            };
          }),
        };
      },
    },
  };
};
```

## 第三方库解析问题
如果一个`esm`的包里使用了`require`来导入`css`文件，就会有如下报错：`Uncaught Error: Dynamic require of "xxx/main.scss" is not supported, when ESM package import commonjs module`
在`vite`里也有相应的[issue](https://github.com/vitejs/vite/issues/5308)，可以通过插件`@originjs/vite-plugin-commonjs`来解决
```js
import { viteCommonjs } from '@originjs/vite-plugin-commonjs'
export default {
    plugins: [
        viteCommonjs()
    ]
}
```
如果引入一个第三方库遇到一堆莫名其妙的报错，可能是该库的打包方式有些问题，可以通过`esbuildCommonjs`处理该第三方库的依赖来解决
```js
import { resolvePackageData } from "vite";
import { esbuildCommonjs } from "@originjs/vite-plugin-commonjs";

// 获取有问题的第三方库依赖
const deps = resolvePackageData("wrong-pkg", __dirname).data
  .dependencies;

export default defineConfig({
  optimizeDeps: {
    esbuildOptions: {
      plugins: [esbuildCommonjs([...Object.keys(deps)])],
    },
  },
});
```
## 通过`optimizeDeps.include`拆包
默认情况下，不在 node_modules 中的，链接的包不会被预构建。使用该配置项可强制预构建链接的包
如果填写第三方库的依赖，可以进行拆包处理
```js
const deps = resolvePackageData("xxxxx", __dirname).data
  .dependencies;

const optimizeDeps = Object.keys(deps).map(
  (item) => `xxxxx > ${item}`
);

{
  optimizeDeps: {
    include: [...optimizeDeps],
  },
}
```
原本在`node_modules`的`.vite`下只会有一个`xxxxx`，在拆包之后就会是`xxxxx_dep1`、`xxxxx_dep2`的形式
