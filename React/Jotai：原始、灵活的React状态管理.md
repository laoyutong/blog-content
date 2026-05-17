## 简述
Jotai采用原子模型（like Recoil），通过组合原子来构建状态
- 简洁的api，易于上手
- 小巧的产物体积（3kb）
- 许多额外的工具和官方集成（immer、optics-ts等）
## 核心使用 
使用atom来创建一个原子配置，参数为初始值
在React组件里通过useAtom进行使用，用法与useState类似；如果只需要获取或者修改值，可以使用useAtomValue或useSetAtom
```js
import { atom, useAtom, useAtomValue } from "jotai";

const counterAtom = atom(0);

const Component = () => {
  const [counter, setCounter] = useAtom(counterAtom);
  return <div onClick={() => setCounter((pre) => pre + 1)}>{counter}</div>;
};
```
atom除了可以直接传一个默认值之外，还可以传一个read，在每次re-render的时候会执行
```js
const counterAtom = atom(0);

const doubleCounterAtom = atom((get) => get(counterAtom) * 2);

const Component = () => {
  const [counter, setCounter] = useAtom(counterAtom);
  const doubleCounter = useAtomValue(doubleCounterAtom);
  return (
    <div onClick={() => setCounter((pre) => pre + 1)}>
      {counter}
      {doubleCounter}
    </div>
  );
};
```
atom还可以接收第二个参数write，通常用于更改原子们的值
 其中write的第三个参数update是useAtom返回的set方法调用传入的参数
```js
const counterAtom = atom(0);

const doubleCounterAtom = atom<number, number>(
  (get) => get(counterAtom) * 2,
  (_, set, update) => set(counterAtom, (pre) => pre + update)
);

const ComponentA = () => {
  const [counter, setCounter] = useAtom(counterAtom);
  const [doubleCounter, setDoubleCounter] = useAtom(doubleCounterAtom);
  return (
    <div>
      <p onClick={() => setCounter((pre) => pre + 1)}>{counter}</p>
      <p onClick={() => setDoubleCounter(2)}>{doubleCounter}</p>
    </div>
  );
};
```
可以在原子配置上添加onMount方法，接收setAtom的参数，返回一个onUnmout方法
如下：当show为true的时候，会打印mount同时增加counterAtom的值；当show切换成false的时候，会打印unmount
```js
const counterAtom = atom(0);

counterAtom.onMount = (set) => {
  console.log("mount");
  set((pre) => pre + 1);
  return () => {
    console.log("unmount");
  };
};

const Component = () => {
  const [counter, setCounter] = useAtom(counterAtom);
  return (
    <div>
      <p onClick={() => setCounter((pre) => pre + 1)}>{counter}</p>
    </div>
  );
};

function App() {
  const [show, setShow] = useState(false);
  return (
    <div>
      <p onClick={() => setShow(!show)}>toggle</p>
      {show ? <Component /> : null}
    </div>
  );
}
```
Provider是一个包含store并在组件树下提供原子值的组件，如果不使用该组件则是有一个默认store的provider-less模式
可以在Provider里传入initialValues定义一些原子默认值
```js
const counterAtom = atom(0);

const Component = () => {
  const counter = useAtomValue(counterAtom);
  return <div>{counter}</div>;  // 1
};

const App = () => (
  <Provider initialValues={[[counterAtom, 1]]}>
    <Component />
  </Provider>
);
```
也可以通过Provider的scope实现作用域的功能，推荐使用唯一的symbol作为值
```js
const counterAtom = atom(0);

const scopeA = Symbol();
const scopeB = Symbol();

const ComponentA = () => {
  const counter = useAtomValue(counterAtom, scopeA);
  return <div>{counter}</div>; // 1
};

const ComponentB = () => {
  const counter = useAtomValue(counterAtom, scopeB);
  return <div>{counter}</div>; // 2
};

const App = () => (
  <>
    <Provider scope={scopeA} initialValues={[[counterAtom, 1]]}>
      <ComponentA />
    </Provider>
    <Provider scope={scopeB} initialValues={[[counterAtom, 2]]}>
      <ComponentB />
    </Provider>
  </>
);
```
## 核心原理
### 基础版
atom就是返回一个配置对象，通过WeakMap去维护原子的状态
WeakMap以原子的配置对象为key，原子的值和监听器作为value
在useAtom中返回的set方法就是修改原子的值并执行监听器里的回调来重新渲染相关的组件
```js
import { useState, useEffect } from 'react'

export const atom = (initialValue) => ({ init: initialValue })

const atomStateMap = new WeakMap()

const getAtomState = (atom) => {
  let atomState = atomStateMap.get(atom)
  if (!atomState) {
    atomState = { value: atom.init, listeners: new Set() }
    atomStateMap.set(atom, atomState)
  }
  return atomState
}

export const useAtom = (atom) => {
  const atomState = getAtomState(atom)
  const [value, setValue] = useState(atomState.value)
  useEffect(() => {
    const callback = () => setValue(atomState.value)
    
    atomState.listeners.add(callback)
    callback()
    
    return () => atomState.listeners.delete(callback)
  }, [atomState])

  const setAtom = (nextValue) => {
    atomState.value = nextValue
    atomState.listeners.forEach((l) => l())
  }
  
  return [value, setAtom]
}
```
### 升级版
对于依赖其他原子的派生原子，为了跟踪所有的依赖项，需要给状态添加一个dependents用于依赖追踪
```js
const getAtomState = (atom) => {
  let atomState = atomStateMap.get(atom)
  if (!atomState) {
    atomState = {
      value: atom.init,
      listeners: new Set(),
      dependents: new Set(),
    }
    atomStateMap.set(atom, atomState)
  }
  return atomState
}
```
atom可以传入read和write两个参数
如果read是一个方法则直接返回参数，否则就构建一个带有read和write的配置，且read里传入的配置和返回的配置是同一个
```js
const atom = (read, write) => {
  if (typeof read === 'function') {
    return { read, write }
  }
  
  const config = {
    init: read,
    read: (get) => get(config),
    write:
      write ||
      ((get, set, arg) => {
        if (typeof arg === 'function') {
          set(config, arg(get(config)))
        } else {
          set(config, arg)
        }
      }),
  }
  return config
}
```
在useAtom中也变成通过readAtom和writeAtom来读取和修改原子
```js
const useAtom = (atom) => {
  const [value, setValue] = useState()
  useEffect(() => {
    const callback = () => setValue(readAtom(atom))
    const atomState = getAtomState(atom)
    atomState.listeners.add(callback)
    callback()
    return () => atomState.listeners.delete(callback)
  }, [atom])
  const setAtom = (nextValue) => {
    writeAtom(atom, nextValue)
  }
  return [value, setAtom]
}
```
在readAtom中，如果get的参数等于readAtom的参数表示是个原始原子，则直接返回原子值即可
否则说明这是一个派生原子，需要读取相应原子的值，并且会添加到dependents里
```js
const readAtom = (atom) => {
  const atomState = getAtomState(atom)
  const get = (a) => {
    if (a === atom) {
      return atomState.value
    }
    const aState = getAtomState(a)
    aState.dependents.add(atom) 
    return readAtom(a)
  }
  const value = atom.read(get)
  atomState.value = value
  return value
}
```
在writeAtom中，会执行原子的write
write中的get就是直接通过getAtomState来获取原子值
write中的set如果修改的原子和writeAtom传入的原子是同一个则会调用notify，不然就继续递归调用writeAtom
```js
const writeAtom = (atom, value) => {
  const atomState = getAtomState(atom)

  const get = (a) => {
    const aState = getAtomState(a)
    return aState.value
  }

  const set = (a, v) => {
    if (a === atom) {
      atomState.value = v
      notify(atom)
      return
    }
    writeAtom(a, v)
  }

  atom.write(get, set, value)
}
```
notify就是会给原子的dependents进行递归执行，并触发原子的listeners
```js
const notify = (atom) => {
  const atomState = getAtomState(atom)
  atomState.dependents.forEach((d) => {
    if (d !== atom) notify(d)
  })
  atomState.listeners.forEach((l) => l())
}
```