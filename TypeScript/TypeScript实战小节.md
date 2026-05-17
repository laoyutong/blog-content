## 常量类型在Array.includes中的报错
在开发中经常会声明一些枚举常量的配置
```ts
const TEST_CONFIG = {
  a: 1,
  b: 2,
} as const
```
在想要判断一个该类型的值是否是其中几个枚举值时，会通过`Array.includes`来判断
但是会发现这种写法有类型错误
```ts
const testValue = Math.ceil(Math.random() * 3) as typeof TEST_CONFIG[keyof typeof TEST_CONFIG]

[TEST_CONFIG.a, TEST_CONFIG.b].includes(testValue)
//  Argument of type '1 | 2 | 3' is not assignable to parameter of type '1 | 2'.
//  Type '3' is not assignable to type '1 | 2'.
```
最简单的是对数组使用`as`来类型断言
```ts
([TEST_CONFIG.a, TEST_CONFIG.b] as number[]).includes(testValue)
```
也可以自定义一个`includes`方法实现类型守卫等功能
```ts

function include<T, P>(arr: T[], target: unknown): target is T {
  return arr.includes(target as any);
}
```