## 前言

`React` 社区生态繁荣，第三方库层出不穷。而在状态管理方面， `Redux` 和 `Mobx` 则是比较流行的两个轮子

## Redux

### 简介

`Redux` 派生于 `Flux` 架构，提倡函数式编程

用单一 `store` 来保存 `state`，使用纯函数来修改 `state`

```jsx
import { createStore } from 'redux'

function counterReducer(state = { value: 0 }, action) {
  switch (action.type) {
    case 'increse':
      return { value: state.value + 1 }
    case 'descrese':
      return { value: state.value - 1 }
    default:
      return state
  }
}
const store = createStore(counterReducer)

store.subscribe(() => console.log(store.getState()))

store.dispatch({ type: 'increse' })
// {value: 1}
store.dispatch({ type: 'increse' })
// {value: 2}
store.dispatch({ type: 'descrese' })
// {value: 1}
```

### react-redux

`Redux` 和 `Mobx` 本身都是纯粹的状态管理库，并没有和 `React` 强绑定，如果想要在 `React` 中使用需要配合 `react-redux` 和 `mobx-react` 来使用

```jsx
import { combineReducers, createStore } from "redux";
import { Provider, useSelector, useDispatch } from "react-redux";

const store = createStore(
  combineReducers({
    count(state = 0, action) {
      const { type } = action;
      switch (type) {
        case "ADD_COUNT":
          return state + 1;
        default:
          return state;
      }
    },
    value(state = 0, action) {
      const { type } = action;
      switch (type) {
        case "ADD_VALUE":
          return state + 1;
        default:
          return state;
      }
    },
  })
);

const Test = () => {
  const { count, value } = useSelector((store) => store);
  const dispatch = useDispatch();
  return (
    <div>
      <h1 onClick={() => dispatch({ type: "ADD_COUNT" })}>{count}</h1>
      <h1 onClick={() => dispatch({ type: "ADD_VALUE" })}>{value}</h1>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <Provider store={store}>
        <Test />
      </Provider>
    </div>
  );
}

export default App;
```

### 原理

`Redux` 通过闭包来维护数据，`createStore`返回三个方法，其中`getState` 用来获取在 `createStore` 中声明的 `currentState` ，通过 `subscribe` 来订阅事件，通过 `reducer` 来修改 `currentState` 的同时，会执行所有 `subscribe` 订阅的事件

```jsx
function createStore(reducer, defaultState) {
  let listeners = [];
  let currentReducer = reducer;
  let currentState = defaultState;

  function dispatch(action) {
    currentState = currentReducer(currentState, action);
    for (let i = 0; i < listeners.length; i++) {
      listeners[i]();
    }
  }

  function getState() {
    return currentState;
  }

  function subscribe(listen) {
    listeners.push(listen);
    return function () {
      listeners = listeners.filter((item) => item !== listen);
    };
  }

  dispatch({
    type: "@@lyt-redux/init",
  });

  return {
    dispatch,
    getState,
    subscribe,
  };
}
```

`react-redux`通过`context` 将 `Redux` 的 `store` 注入到 `Provider`中，通过 `useContext` 即可获取`store`中的数据。为了使 `state` 发生变化的时候触发相应组件的更新，通过 `subscribe` 来订阅 `forceUpdate` ，当 `dispatch` 执行 `reducer` 更新 `state` 的时候，使用了 `state` 的组件就会触发订阅，更新组件

```jsx
import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useState,
} from "react";

const storeCtx = createContext();

function Provider({ store, children }) {
  return <storeCtx.Provider value={store}>{children}</storeCtx.Provider>;
}

function useSelector(state) {
  const store = useStore();
  const forceUpdate = useForceUpdate();
  
  useLayoutEffect(() => {
    const sub = store.subscribe(() => forceUpdate());
    return () => sub();
  }, [forceUpdate, store]);
  return state(store.getState());
}

function useDispatch() {
  const { dispatch } = useStore();
  return dispatch;
}

function useStore() {
  const store = useContext(storeCtx);
  return store;
}

function useForceUpdate() {
  const [, setState] = useState(0);
  const forceUpdate = useCallback(() => setState((p) => p + 1), []);
  return forceUpdate;
}
```

如上的实现比较简单粗暴，使用了`useSelector`的地方都会触发更新，但在源码实现中，会缓存上一次的值，通过比较来判断是否需要更新

```jsx
useIsomorphicLayoutEffect(() => {
    latestSelector.current = selector
    latestStoreState.current = storeState
    latestSelectedState.current = selectedState
    latestSubscriptionCallbackError.current = undefined
  })

useIsomorphicLayoutEffect(() => {
function checkForUpdates() {
  try {
    const newStoreState = store.getState()
    const newSelectedState = latestSelector.current!(newStoreState)

    if (equalityFn(newSelectedState, latestSelectedState.current)) {
      return
    }

    latestSelectedState.current = newSelectedState
    latestStoreState.current = newStoreState
  } catch (err) {
    // we ignore all errors here, since when the component
    // is re-rendered, the selectors are called again, and
    // will throw again, if neither props nor store state
    // changed
    latestSubscriptionCallbackError.current = err as Error
  }

  forceRender()
}

subscription.onStateChange = checkForUpdates
subscription.trySubscribe()

checkForUpdates()
```

## Mobx

### 简介

`Mobx` 通过透明的函数式响应编程使状态管理变得简单和可拓展

通过`proxy`来实现数据的双向绑定，使状态变得可观察，视图可以响应状态的变化

```jsx
import React from "react"
import ReactDOM from "react-dom"
import { makeAutoObservable } from "mobx"
import { observer } from "mobx-react"

// 对应用状态进行建模。
class Timer {
    secondsPassed = 0

    constructor() {
        makeAutoObservable(this)
    }

    increase() {
        this.secondsPassed += 1
    }

    reset() {
        this.secondsPassed = 0
    }
}

const myTimer = new Timer()

// 构建一个使用 observable 状态的“用户界面”。
const TimerView = observer(({ timer }) => (
    <button onClick={() => timer.reset()}>已过秒数：{timer.secondsPassed}</button>
))

ReactDOM.render(<TimerView timer={myTimer} />, document.body)

// 每秒更新一次‘已过秒数：X’中的文本。
setInterval(() => {
    myTimer.increase()
}, 1000)
```

### 原理

响应式的核心原理就是在`get`的时候`track`收集依赖，然后在`set`的时候`triggle`执行

```jsx
import {
  memo,
  useState,
  useRef,
  FunctionComponent,
  MemoExoticComponent,
} from "react";

type Effect = () => void;
type ProxyKey = string | symbol;

const effectStack: Effect[] = [];

const targetMap = new WeakMap<object, Map<ProxyKey, Effect[]>>();

function isObject(v: any): boolean {
  return v && typeof v === "object";
}

function track(target: object, key: ProxyKey) {
  let deps = targetMap.get(target);
  if (!deps) {
    deps = new Map();
    targetMap.set(target, deps);
  }

  let effectList = deps.get(key);
  if (!effectList) {
    effectList = [];
    deps.set(key, effectList);
  }

  if (effectStack.length !== 0) {
    effectList.push(effectStack[effectStack.length - 1]);
  }
}

function triggle(target: object, key: ProxyKey) {
  let deps = targetMap.get(target);
  if (!deps) {
    return;
  }

  const effectList = deps.get(key);
  if (effectList) {
    effectList.forEach((effect) => effect());
  }
}

function createObserable(target: any) {
  if (!isObject(target)) {
    return target;
  }
  for (let i in target) {
    target[i] = createObserable(target[i]);
  }
  return new Proxy(target, {
    get(target, key) {
      track(target, key);
      return Reflect.get(target, key);
    },
    set(target, key, value) {
      const r = Reflect.set(target, key, value);
      triggle(target, key);
      return r;
    },
  });
}

function useObserver<T extends () => any>(component: T): ReturnType<T> {
  const [_, forceUpdate] = useState([]);

  const result = useRef<ReturnType<T>>();

  if (!result.current) {
    effectStack.push(() => forceUpdate([]));
    result.current = component();
    effectStack.pop();
  } else {
    result.current = component();
  }
  return result.current as ReturnType<T>;
}

function obserable<T extends object>(target: T): T {
  return createObserable(target);
}

function observer<T>(
  component: FunctionComponent<T>
): MemoExoticComponent<FunctionComponent> {
  const WrapperComponent = (props: any) => {
    return useObserver(() => component(props));
  };
  return memo(WrapperComponent as any);
}
```