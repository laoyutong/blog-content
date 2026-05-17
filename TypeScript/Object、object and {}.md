- Object包含所有类型

```tsx
const a1: Object = 123
const a2: Object = 'string'
const a3: Object = []
const a4: Object = {}
const a5: Object = false
const a6: Object = Symbol()
```

- object包含非原始类型

```tsx
const a1: object = 'string';  // X 不成立
const a2: object = 123; // X 不成立

const a3: object = {};
const a4: object = () => {};
const a5: object = [];
```

- {}和Object类似，也包含所有类型

```tsx
const a1: {} = 123
const a2: {} = 'string'
const a3: {} = []
const a4: {} = {}
const a5: {} = false
const a6: {} = Symbol()
```

{}和Object的区别是：Object上会有一些内置方法的定义，但是{}上则没有

```tsx
const a1: Object = { toString: () => 123 }
// Type 'number' is not assignable to type 'string'.(2322)

const a1: {} = { toString: () => 123 }
```