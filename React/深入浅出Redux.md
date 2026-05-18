## Redux
> JS 应用程序的可预测状态容器
### 基本使用
**createStore(reducer, [preloadedState], [enhancer])**
创建一个store
```js
import { createStore } from 'redux'

function counterReducer(state = { value: 0 }, action) {
  switch (action.type) {
    case 'incremented':
      return { value: state.value + 1 }
    case 'decremented':
      return { value: state.value - 1 }
    default:
      return state
  }
}
const store = createStore(counterReducer)

store.subscribe(() => console.log(store.getState()))

store.dispatch({ type: 'incremented' })
// {value: 1}
store.dispatch({ type: 'incremented' })
// {value: 2}
store.dispatch({ type: 'decremented' })
// {value: 1}
```
**combineReducers(reducers)**
将多个reducer函数合并成一个
```js
const rootReducer = combineReducers({potato: potatoReducer, tomato: tomatoReducer})
```
**applyMiddleware(...middleware)**
添加中间件
```js
import { createStore, applyMiddleware } from 'redux'
import reducer from './reducers'

function logger({ getState }) {
  return next => action => {
    console.log('will dispatch', action)
    const returnValue = next(action)
    console.log('state after dispatch', getState())
    return returnValue
  }
}

const store = createStore(reducer, applyMiddleware(logger))
```
### 原理解析
`createStore`方法内部维护两个变量`currentState`和`currentReducer`
通过`dispatch`来执行`currentReducer`来修改`currentState`的值，同时执行所有通过`subscribe`注册的函数
在函数里需要调用一次`dispatch`且`action`的类型是唯一的，来获取`reducer`方法里的默认值
```js
 function createStore(reducer, defaultState) {
  if (typeof enhancer !== "undefined") {
    return enhancer(createStore)(reducer, defaultState);
  }
 
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
`combineReducers`最终也是返回一个`reducer`方法，里面会执行参数配置中所有的`reducer`，将其状态合并后返回
```js
export default function combineReducers (reducers) {
  return function (state = {}, action) {
    const combineState = {};
    for (const key in reducers) {
      if (reducers.hasOwnProperty(key)) {
        combineState[key] = reducers[key](state[key], action);
      }
    }
    return combineState;
  };
}
```
通过`compose`函数依次执行中间件函数
最终返回一个增强后的`dispatch`
```js
function compose(...funcs) {
    return funcs.reduce((a, b) => (...args) => a(b(...args)))
}

export default function applyMiddleware(...middlewares) {
  return function (createStore) {
    return function (reducer, defaultState) {
      const store = createStore(reducer, defaultState);

      const simpleStore = {
        getState: store.getState,
        dispatch: store.dispatch,
      };
      const middlewaresChain = middlewares.map((middleware) =>
        middleware(simpleStore)
      );

      const dispatch = compose(...middlewaresChain)(store.dispatch);

      return {
        ...store,
        dispatch,
      };
    };
  };
}
```
## React-Redux
React UI的绑定层，使React组件可以从`Redux`中读取数据，并派发`action`来修改状态
### 基本使用
提供了一个`Provider`组件，将`createStore`的返回值传进去
```js
import React from 'react'
import ReactDOM from 'react-dom'
import { Provider } from 'react-redux'
import store from './store'
import App from './App'

ReactDOM.render(
  <Provider store={store}>
    <App />
  </Provider>,
  document.getElementById('root')
)
```
通过`useSelector`来获取`store`中的数据
通过`useDispatch`来获取`dispatch`方法，可以派发`action`来修改状态
```js
import React from 'react'
import { useSelector, useDispatch } from 'react-redux'

export function Counter() {
  const count = useSelector(store=>store.count)
  const dispatch = useDispatch()

  return (
    <div>
     {count}
     <button onClick={()=>dispatch({type:'add'})}>增加</button>
     <button onClick={()=>dispatch({type:'reduce'})} >减少</button>
    </div>
  )
}
```
### 原理浅析
`Provider`通过`createContext`将`store`注入进去
```js
const storeCtx = createContext();

export function Provider({ store, children }) {
  return <storeCtx.Provider value={store}>{children}</storeCtx.Provider>;
}
```
`useDispatch`就是通过`useContext`来获取`store`上的`dispatch`方法
`useSelector`则是获取`getState`方法，同时需要通过`subscribe`来注册监听器，当使用`dispatch`更改状态时，更新使用了`store`里数据的组件
```js
function useStore() {
  const store = useContext(storeCtx);
  return store;
}

export function useSelector(state) {
  const store = useStore();
  const forceUpdate = useForceUpdate();
  useLayoutEffect(() => {
    const sub = store.subscribe(() => forceUpdate());
    return () => sub();
  }, [forceUpdate, store]);
  return state(store.getState());
}

export function useDispatch() {
  const { dispatch } = useStore();
  return dispatch;
}
```
源码实现中会进行比较判断，当前后的值不同时才执行`forceRender`
```js
 function checkForUpdates() {
      try {
        const newStoreState = store.getState()
        if (newStoreState === latestStoreState.current) {
          return
        }

        const newSelectedState = latestSelector.current(newStoreState)
        if (equalityFn(newSelectedState, latestSelectedState.current)) {
          return
        }
        
        latestSelectedState.current = newSelectedState
        latestStoreState.current = newStoreState
      } catch (err) {
        latestSubscriptionCallbackError.current = err
      }
      forceRender()
}
checkForUpdates()
```
## Redux Toolkit
目的是成为编写 Redux 逻辑的标准方法
### configureStore
参数和`createStore`类似
```js
interface ConfigureStoreOptions<
  S = any,
  A extends Action = AnyAction,
  M extends Middlewares<S> = Middlewares<S>
> {
  reducer: Reducer<S, A> | ReducersMapObject<S, A>
  middleware?: ((getDefaultMiddleware: CurriedGetDefaultMiddleware<S>) => M) | M
  devTools?: boolean | DevToolsOptions
  preloadedState?: DeepPartial<S extends any ? S : S>
}

function configureStore<S = any, A extends Action = AnyAction>(
  options: ConfigureStoreOptions<S, A>
): EnhancedStore<S, A>
```
**基本使用**
```js
const store = configureStore({
  reducer:(state = { value: 0 }, action) {
      switch (action.type) {
        case 'incremented':
          return { value: state.value + 1 }
        case 'decremented':
          return { value: state.value - 1 }
        default:
          return state
      }
  },
  devTools: process.env.NODE_ENV !== 'production',
})
```
**简单实现**
如果`reducer`不是函数则调用`combineReducers`来进行合并
默认集成了`redux-thunk`中间件
```js
import { createStore, combineReducers, applyMiddleware } from "redux";
import thunk from "redux-thunk";

export const configureStore = ({
  reducer,
  middleware = [thunk],
  preloadedState,
}) => {
  return createStore(
    typeof reducer === "function" ? reducer : combineReducers(reducer),
    preloadedState,
    applyMiddleware(...middleware)
  );
};
```
### createAction
手动创建`action creator`函数
```js
const INCREMENT = 'counter/increment'

function increment(amount: number) {
  return {
    type: INCREMENT,
    payload: amount,
  }
}

const action = increment(3)
// { type: 'counter/increment', payload: 3 }
```
通过`createAction`创建
```js
import { createAction } from '@reduxjs/toolkit'

const increment = createAction<number | undefined>('counter/increment')

let action = increment()
// { type: 'counter/increment' }

action = increment(3)
// returns { type: 'counter/increment', payload: 3 }

console.log(increment.toString())
// 'counter/increment'
```
可以通过`prepareAction`来定制`action`的内容
```js
import { createAction, nanoid } from '@reduxjs/toolkit'
const addTodo = createAction('todos/add', function prepare(text: string) {
  return {
    payload: {
      text,
      id: nanoid(),
      createdAt: new Date().toISOString(),
    },
  }
})
console.log(addTodo('Write more docs'))
/**
 * {
 *   type: 'todos/add',
 *   payload: {
 *     text: 'Write more docs',
 *     id: '4AJvwMSWEHCchcWYga3dj',
 *     createdAt: '2019-10-03T07:53:36.581Z'
 *   }
 * }
 **/
```
**简单实现**
```js
export const createAction = (type, prepareAction) => {
  const actionCreator = (payload) => ({
    type,
    payload: prepareAction ? prepareAction(payload).payload : payload,
  });
  actionCreator.toString = () => `${type}`
  actionCreator.type = type;
  return actionCreator;
};
```
### createReducer
直接定义`reducer`函数
```js
function counterReducer(state = { value: 0 }, action) {
  switch (action.type) {
    case 'increment':
      return { ...state, value: state.value + 1 }
    case 'decrement':
      return { ...state, value: state.value - 1 }
    case 'incrementByAmount':
      return { ...state, value: state.value + action.payload }
    default:
      return state
  }
}
```
`createReducer`可以简化`reducer`函数的创建，同时内置了`immer`
```js
const increment = createAction('increment')
const decrement = createAction('decrement')

const counterReducer = createReducer({ count:0 }, {
  [increment]: (state, action) => {
      state.count += action.payload
  },
  [decrement.type]: (state, action) => {
      state.count -= action.payload
  }
})
```
**简单实现**
```js
import produce from "immer";
export const createReducer = (initialState, actionsMap) => {
  return (state = initialState, action) => {
    const reducer = actionsMap[action.type];
    if (reducer) {
      return produce(state, (draft) => {
        reducer(draft, action);
      });
    }
    return state;
  };
};
```
### createSlice
一个接受默认值、`reducer` 函数和切片名称的函数，并自动生成与`reducer` 和`state`对应的`action creator`和`action type`
```js
import { createSlice } from '@reduxjs/toolkit'

const counterSlice = createSlice({
  name: 'counter',
  initialState: 0,
  reducers: {
    increment: (state) => state + 1,
  },
})
// action type `'counter/increment'`
export const { increment } = counterSlice.actions
export default counterSlice.reducer
```
内部使用了`createAction`和`createReducer`
```js
const createSlice = ({ name, initialState, reducers }) => {
  const actions = {};
  const prefixActionsMap = {};
  Object.keys(reducers).forEach((actionType) => {
    const prefixActionType = name + "/" + actionType;
    actions[actionType] = createAction(prefixActionType);
    prefixActionsMap[prefixActionType] = reducers[actionType];
  });
  return {
    reducer: createReducer(initialState, prefixActionsMap),
    actions,
  };
};
```