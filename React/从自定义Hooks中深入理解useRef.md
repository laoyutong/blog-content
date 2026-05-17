# 前言

经历了几次React的需求开发后，感觉对React Hooks的理解还不够深入，经历了N次Code Review的灵魂拷问（手动狗头），为了提高项目的开发质量，于是打算通过学习开源的自定义Hooks来加深理解

# useRef简介

```jsx
const refContainer = useRef(initialValue);
```

- `useRef` 返回一个可变对象，其 `.current` 属性初始化为传入的参数`initialValue`
- 本质上 `useRef` 就像是可以在其 `.current` 属性上保存一个可变值的容器
- `useRef` 创建的就是一个普通的 JavaScript 对象，而和直接声明一个 `{current:...}` 的唯一区别就是 `useRef` 在每次渲染时都会返回同一个对象
- 修改 `.current` 属性不会导致组件的重新渲染

# useCreation

`useCreation` 是 `useMemo` 或 `useRef` 的替代品

React官网关于 `useMemo` 的介绍：

> **You may rely on useMemo as a performance optimization, not as a semantic guarantee**. In the future, React may choose to “forget” some previously memoized values and recalculate them on next render, e.g. to free memory for offscreen components. Write your code so that it still works without `useMemo` — and then add it to optimize performance

简单来说， `useMemo` 不能保证被memo的值一定不会被重新计算

而 `useRef` 在创建复杂对象的常量时可能会有性能隐患

```jsx
class Factory {
  constructor() {
    console.log("constructor");
    this.name = "name";
  }
}

function Demo() {
  const [count, setCount] = useState(0);

  const factory = useRef(new Factory());

  return <div onClick={() => setCount(count + 1)}>{factory.current.name}</div>;
}
```

每次点击的时候， `count++` 导致 `Demo` 组件重新渲染，“constructor” 都会被打印在控制台中，即 `Factory` 被重新实例化了，明显是没有必要的

`useCreation`的具体实现：

```jsx
import { useRef } from 'react';

export default function useCreation<T>(factory: () => T, deps: any[]) {
  const { current } = useRef({
    deps,
    obj: undefined as undefined | T,
    initialized: false,
  });
  if (current.initialized === false || !depsAreSame(current.deps, deps)) {
    current.deps = deps;
    current.obj = factory();
    current.initialized = true;
  }
  return current.obj as T;
}

function depsAreSame(oldDeps: any[], deps: any[]): boolean {
  if (oldDeps === deps) return true;
  for (let i = 0; i < oldDeps.length; i++) {
    if (oldDeps[i] !== deps[i]) return false;
  }
  return true;
}
```

代码也比较简单，通过 `useRef` 声明一个对象，属性分别为依赖项、返回的值、是否为初始化的标识

只有在初始化和依赖项发生变化的时候，`factory` 才会重新执行并给 `currrent.obj` 赋值，避免了性能隐患

# usePersistFn

用于持久化 `function` 的 `hook` 

如下例子：

```jsx
const [count, setCount] = useState(0);

const showCountPersistFn = usePersistFn(() => {
  console.log(`count is ${count}`);
});

const showCountCommon = useCallback(() => {
  console.log(`count is ${count}`);
}, [count]);
```

当 `count` 发生变化的时候， `showCountCommon` 的函数地址就会发生变化，当作为子组件的回调函数时，会导致子组件重新渲染

但是 `showCountPersistFn` 可以保证函数地址永远不会变化

`usePersistFn` 的具体实现如下：

```jsx
import { useRef } from 'react';

export type noop = (...args: any[]) => any;

function usePersistFn<T extends noop>(fn: T) {
  const fnRef = useRef<T>(fn);
  fnRef.current = fn;

  const persistFn = useRef<T>();
  if (!persistFn.current) {
    persistFn.current = function (...args) {
      return fnRef.current!.apply(this, args);
    } as T;
  }

  return persistFn.current!;
}

export default usePersistFn;
```

通过 `useRef` 声明的 `fnRef` 来存储需要持久化的 `fn` ，即使组件重新渲染， `fnRef` 上存储的也是最新的 `fn`

`usePersistFn` 会返回一个通过 `useRef` 声明的 `persistFn` ，给 `persistFn.current` 赋值一个匿名函数，在该函数中执行 `fnRef.current` ，并返回执行的结果即可，并且每次改变的仅仅是 `fnRef` 的函数地址，而 `usePersistFn` 不会重新赋值，从始至终都是那一个匿名函数，所以可以保证函数地址的一致

## 总结

- 通常情况下，可以用 `useRef` 存储一些变更时无需使组件重新渲染的数据
- 在 `useRef` 中需要尽量避免创建复杂对象，因为每次组件渲染都会重新实例化
- 通过使用 `useRef` 可以在保证函数地址始终相同的同时，函数执行的结果也是预期的，可以替代 `useCallback` 来使用