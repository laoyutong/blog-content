> 如何低成本精确context的渲染范围❓❓❓

在跨组件数据传递的场景，通常会使用`context`来替代`props`的层层传递
`Provider`里`value`更新的时候，使用了`useContext`的组件都会`re-render`
```js
const context = createContext(null);

const ContextWrapper = ({ children }) => (
  <context.Provider value={useState({ a: 0, b: 0 })}>
    {children}
  </context.Provider>
);

const ComponentA = () => {
  const [value, setValue] = useContext(context);
  console.log("ComponentA:::render");
  return (
    <div onClick={() => setValue((pre) => ({ ...pre, a: pre.a + 1 }))}>
      a:{value.a}
    </div>
  );
};

const ComponentB = () => {
  const [value, setValue] = useContext(context);
  console.log("ComponentB:::render");
  return (
    <div onClick={() => setValue((pre) => ({ ...pre, b: pre.b + 1 }))}>
      b:{value.b}
    </div>
  );
};

const ComponentC = () => {
  console.log("ComponentC:::render");
  return <div>c</div>;
};

const App = () => (
  <ContextWrapper>
    <>
      <ComponentA />
      <ComponentB />
      <ComponentC />
    </>
  </ContextWrapper>
);

// click a
// ComponentA:::render
// ComponentB:::render

// click b
// ComponentA:::render
// ComponentB:::render
```
一方面可以对`value`进行合理拆分，使用多个`Provider`来注入原始类型的数据
```js
const contextA = createContext(null);
const contextB = createContext(null);

const ContextA = ({ children }) => (
  <contextA.Provider value={useState(0)}>{children}</contextA.Provider>
);

const ContextB = ({ children }) => (
  <contextB.Provider value={useState(0)}>{children}</contextB.Provider>
);

const ComponentA = () => {
  const [value, setValue] = useContext(contextA);
  console.log("ComponentA:::render");
  return <div onClick={() => setValue((pre) => pre + 1)}>a:{value}</div>;
};

const ComponentB = () => {
  const [value, setValue] = useContext(contextB);
  console.log("ComponentB:::render");
  return <div onClick={() => setValue((pre) => pre + 1)}>b:{value}</div>;
};

const App = () => (
  <>
    <ContextA>
      <ComponentA />
    </ContextA>
    <ContextB>
      <ComponentB />
    </ContextB>
  </>
);

// click a
// ComponentA:::render

// click b
// ComponentB:::render
```
也可以用`use-context-selector`这种第三方库来替代原生的`createContext`
在点击`ComponentB`的时候，可以发现`ComponentA`里的渲染的`Math.random`没有发生变化，反之亦然
```js
import { useState } from "react";
import { createContext, useContextSelector } from "use-context-selector";

const context = createContext(null);

const Context = ({ children }) => (
  <context.Provider value={useState({ a: 1, b: 2 })}>
    {children}
  </context.Provider>
);

const ComponentA = () => {
  const value = useContextSelector(context, (pre) => pre[0].a);
  const setValue = useContextSelector(context, (pre) => pre[1]);
  console.log("ComponentA:::render");
  return (
    <div onClick={() => setValue((pre) => ({ ...pre, a: pre.a + 1 }))}>
      a:{value}:::{Math.random()}
    </div>
  );
};

const ComponentB = () => {
  const value = useContextSelector(context, (pre) => pre[0].b);
  const setValue = useContextSelector(context, (pre) => pre[1]);
  console.log("ComponentB:::render");
  return (
    <div onClick={() => setValue((pre) => ({ ...pre, b: pre.b + 1 }))}>
      b:{value}:::{Math.random()}
    </div>
  );
};

const App = () => (
  <Context>
    <ComponentA />
    <ComponentB />
  </Context>
);
```
虽然`Math.random`的渲染没有发生变化，但是发现函数组件还是执行了，打印了`render`❓❓❓
官方文档和`Dan Abrahmov`有对该现象的回答：
- 虽然会重新`render`这个组件，但是不会继续深入整棵树，对于`render`时有耗时计算的场景可以使用`useMemo`来优化
- 对于内联`reducer`的情况需要重新执行`reducer`之后才能知道是否需要`bailout`，所以需要在`rende`阶段的更新上重新执行
- `bailout`并不阻止调用渲染，而是阻止渲染子组件

> From https://reactjs.org/docs/hooks-reference.html#usereducer:
Bailing out of a dispatch
If you return the same value from a Reducer Hook as the current state, React will bail out without rendering the children or firing effects (React uses the Object.is comparison algorithm)
Note that React may still need to render that specific component again before bailing out. That shouldn’t be a concern because React won’t unnecessarily go “deeper” into the tree. If you’re doing expensive calculations while rendering, you can optimize them with useMemo

> From Dan:
I think at the time we decided that we don't actually know if it's safe to bail out in all cases until we try render again. The "bailout" here means that it doesn't go ahead to render children. But re-running the same function might be necessary (for example, if a reducer is inline and we don't know if we bail out until we re-run the reducer on next render). So for consistency we always re-run it on updates during the render phase.
The bailout isn’t supposed to prevent calling the render. It prevents rendering child components. So you shouldn’t worry about this component’s own render running again.

`use-context-selector`的核心原理就是控制`Provider`的`value`不变，对于`selector`的值变化的组件手动触发更新
```js
import { useEffect, useRef, useReducer } from "react";
import {
  createContext as createOriginContext,
  createElement,
  useContext,
} from "react";

// context还是用原生的创建，但是Provider会自定义
export const createContext = (defaultValue) => {
  const context = createOriginContext(defaultValue);
  context.Provider = createProvider(context.Provider);
  return context;
};

// 会将value的值存储在对象里，并有一个事件监听的Set
// 当value改变的时候这个对象的引用地址不会变，只修改这个对象上的属性
// 所以原生的context不会触发渲染
// 通过触发listeners使订阅context的组件渲染
const createProvider = (OriginProvider) => {
  const ContextProvider = ({ value, children }) => {
    const contextValue = useRef();
    if (!contextValue.current) {
      contextValue.current = {
        value,
        listeners: new Set(),
      };
    }

    useEffect(() => {
      contextValue.current.value = value;
      contextValue.current.listeners.forEach((item) => item());
    }, [value]);

    return createElement(
      OriginProvider,
      { value: contextValue.current },
      children
    );
  };
  return ContextProvider;
};

// 所有使用useContextSelector的组件都会触发dispatch
// 但是在useReducer的reducer中会判断前后的值，如果一致就直接返回之前的值，不会触发渲染
export const useContextSelector = (contextIns, selector) => {
  const contextValue = useContext(contextIns);
  const selected = selector(contextValue.value);

  const [state, dispatch] = useReducer(
    (pre) => {
      if (selector(pre[0]) === selected) {
        return pre;
      }
      return [contextValue.value, selected];
    },
    [contextValue.value, selected]
  );

  useEffect(() => {
    contextValue.listeners.add(dispatch);
    return () => {
      contextValue.listeners.delete(dispatch);
    };
  }, [contextValue.listeners]);

  return state[1];
};

```