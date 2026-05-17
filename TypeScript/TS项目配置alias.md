在 `vite` 中配置 `alias`(在 `webpack` 或者 `babel` 中配置也是同理)

💡注：需要下载 `@types/node` 才可以正常引入 `path` 和使用 `__dirname`

```jsx
import { defineConfig } from "vite";
import path from "path";

export default defineConfig({
  resolve: {
    alias: [
      {
        find: "@",
        replacement: path.resolve(__dirname, "src"),
      },
    ],
  },
});
```

配置完成后，会发现代码是可以正常运行的，但是在编辑器里会报错

```jsx
import Login from *"@/pages/Login*"; 

// Cannot find module '@/pages/Login' or its corresponding type declarations.ts(2307)
```

解决方案：需要在 `tsconfig.json` 里的`compilerOptions`中加上 `baseUrl` 和 `paths`

```jsx
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```