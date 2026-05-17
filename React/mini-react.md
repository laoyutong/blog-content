## createElement
在React中通常使用JSX这一种语法拓展，可以很好地描述 UI 应该呈现出它应有交互的本质形式
但是在浏览器中无法直接使用JSX。在17版本之前，会通过Babel来将JSX转换成JavaScript代码，即React.createElement
```jsx
// 源代码
import React from 'react';

function App() {
  return <h1>Hello World</h1>;
}

// 转换后
import React from 'react';

function App() {
  return React.createElement('h1', null, 'Hello world');
}
```
createElement的实现比较简单，就返回一个Virtual Dom，简单来说就是一个对象
将children放到props里，所以children可以直接通过props.children来获取

但是需要额外判断一下children是字符串、数字等情况
返回一个type为TEXT_NODE的对象即可，然后把值放到props的nodeValue中，以便后续统一处理
```jsx
function createElement(type, props, ...children) {
  return {
    type,
    props: {
      ...props,
      children: children.map((child) => {
        return typeof child === "object" ? child : createTextElement(child);
      }),
    
  };
}

function createTextElement(text) {
  return {
    type: "TEXT_NODE",
    props: {
      nodeValue: text,
    },
  };
}
```
## render
实现一个简单的render方法，把我们createElement返回的virtual dom渲染到页面上

类型是TEXT_NODE的通过createTextNode生成，其他的则通过createElement
先简单处理，直接将props除了children的属性全都放到dom上
children通过递归执行render
最后将生成的DOM添加到container中
```jsx
function render(vdom, container) {
  const dom =
    vdom.type === "TEXT_NODE"
      ? document.createTextNode("")
      : document.createElement(vdom.type);

  vdom.props.children.forEach((child) => {
    render(child, dom);
  });
  
  Object.keys(vdom.props)
    .filter((key) => key !== "children")
    .forEach((key) => (dom[key] = vdom.props[key]));

  container.appendChild(dom);
}
```
示例代码:(为了省事没有使用Babel等工具进行JSX的转换，所以直接写成createElement的形式)
```jsx
<div id="root"></div>
<script src="react.js"></script>
<script>
  const element = createElement(
    "h1",
    { className: "title" },
    createElement("span", {}, "hello"),
    createElement("span", {}, "world")
  );
  render(element, document.getElementById("root"));
</script>
```
## Concurrent Mode
render是通过递归来实现的，项目太过复杂就容易使JavaScript的执行时间过久，从而导致页面卡顿
所以想将render分成更小的工作单元，每完成一个单元的工作，允许浏览器打断来处理其他的事情
通过requestIdleCallback来进行简单实现，浏览器在线程空闲的时候主动执行回调函数

用全局变量nextUnitOfWork表示下一个工作单元
deadline是requestIdleCallback给回调函数的参数，用来获取这个渲染周期的剩余时间
当有下一个工作单元且还有剩余时间的时候执行performUnitOfWork函数
在这个函数中会进行工作单元的处理，并返回下一个工作单元
```jsx
let nextUnitOfWork = null;

function wookLoop(deadline) {
  if (nextUnitOfWork && deadline.timeRemaining() > 1) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
  }
  requestIdleCalback(wookLoop);
}
requestIdleCalback(wookLoop);

function performUnitOfWork() {
    // TODO
}
```
通过Fiber这种数据结构来描述工作单元，每一个Fiber都是一个单元任务
通过child来连接第一个子节点，其他的子节点都通过sibling根据第一个子节点依次连接，且都通过parent连接到父节点

先进行一下代码逻辑的调整
将render中创建dom的逻辑提取为createDom
```jsx
function createDom(vdom) {
  const dom =
    vdom.type === "TEXT_NODE"
      ? document.createTextNode("")
      : document.createElement(vdom.type);

  Object.keys(vdom.props)
    .filter((key) => key !== "children")
    .forEach((key) => (dom[key] = vdom.props[key]));

  return dom;
}
```
在render函数中进行nextUnitOfWork的赋值
```jsx
function render(vdom, container) {
  nextUnitOfWork = {
    dom: container,
    props: {
      children: [vdom],
    },
  };
}
```
在performUnitOfWork中，主要做三个事情
1. 创建dom节点
2. 给子节点创建fiber
3. 返回下一个单元任务
```jsx
function performUnitOfWork(fiber) {
  // 1 创建dom节点
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }
  if (fiber.parent) {
    fiber.parent.dom.appendChild(fiber.dom);
  }

  // 2 给子节点创建fiber
  let index = 0;
  let prevSibling = null;
  const elements = fiber.props.children;
  while (index < elements.length) {
    const element = elements[index];
    const newFiber = {
      parent: fiber,
      type: element.type,
      props: element.props,
      dom: null,
    };

    if (index === 0) {
      fiber.child = newFiber;
    } else {
      prevSibling.sibling = newFiber;
    }
    index++;
    prevSibling = newFiber;
  }

  // 3 返回下一个工作单元
  if (fiber.child) {
    return fiber.child;
  }
  let nextFiber = fiber;
  while (nextFiber) {
    if (nextFiber.sibling) {
      return nextFiber.sibling;
    }
    nextFiber = nextFiber.parent;
  }
  return null;
}
```
## workInProgress
当我们用canvas绘制动画，每一帧绘制前都会调用ctx.clearRect清除上一帧的画面
如果当前帧画面计算量比较大，导致清除上一帧画面到绘制当前帧画面之间有较长间隙，就会出现白屏
为了解决这个问题，我们可以在内存中绘制当前帧动画，绘制完毕后直接用当前帧替换上一帧画面，由于省去了两帧替换间的计算时间，不会出现从白屏到出现画面的闪烁情况。
这种在内存中构建并直接替换的技术叫做双缓存

React使用“双缓存”来完成Fiber树的构建与替换——对应着Dom树的创建与更新
在React中最多会同时存在两棵Fiber树。当前屏幕上显示内容对应的Fiber树称为current fiber树
正在内存中构建的Fiber树称为workInProgress fiber 树

声明一个全局变量wipRoot，来表示构建中的fiber树
修改render的逻辑,给wipRoot赋值
```jsx
function render(vdom, container) {
  wipRoot = {
    dom: container,
    props: {
      children: [vdom],
    },
  };
  nextUnitOfWork = wipRoot;
}
```
在wookLoop中，当wipRoot构建完毕后，即nextUnitOfWork为null的时候进行提交
```jsx
function wookLoop(deadline) {
  if (nextUnitOfWork && deadline.timeRemaining() > 1) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
  }
  if (!nextUnitOfWork && wipRoot) {
    commitWork(wipRoot);
    wipRoot = null;
  }
  requestIdleCallback(wookLoop);
}

function commitWork(wipFiber) {
  if (!wipFiber) {
    return;
  }
  if (wipFiber.parent) {
    wipFiber.parent.dom.appendChild(wipFiber.dom);
  }
  commitWork(wipFiber.child);
  commitWork(wipFiber.sibling);
}
```
## Reconciliation
目前只处理了页面挂载阶段时新加节点的情况
在页面更新时需要比较上次的fiber和当前渲染的fiber来决定哪些节点需要更新

全局声明一个变量currentRoot来保存上一次的fiber树
```jsx
function wookLoop(deadline) {
  if (nextUnitOfWork && deadline.timeRemaining() > 1) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
  }
  if (!nextUnitOfWork && wipRoot) {
    commitWork(wipRoot);
    currentRoot = wipRoot;
    wipRoot = null;
  }
  requestIdleCallback(wookLoop);
}
```
同时给每一个fiber节点一个base属性指向上一次渲染的fiber
```jsx
function render(vdom, container) {
  wipRoot = {
    dom: container,
    props: {
      children: [vdom],
    },
    base: currentRoot,
  };
  nextUnitOfWork = wipRoot;
}
```
在perfromUnitOfWork中执行reconcileChildren
```jsx
function performUnitOfWork(fiber) {
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }

  const elements = fiber.props.children;
  reconcileChildren(fiber, elements);

  if (fiber.child) {
    return fiber.child;
  }

  let nextFiber = fiber;
  while (nextFiber) {
    if (nextFiber.sibling) {
      return nextFiber.sibling;
    }
    nextFiber = nextFiber.parent;
  }
  return null;
}
```
在reconcileChildren中进行新旧fiber的比较 打上effectTag
```jsx
function reconcileChildren(wipFiber, elements) {
  let index = 0;
  let prevSibling = null;
  let oldFiber = fiber.base?.child;

  while (index < elements.length && oldFiber) {
    const element = elements[index];
    let newFiber = null;
    const sameType = element && oldFiber && oldFiber.type === element.type;
    // 如果前后fiber的type相同，则可以进行复用
    // 只需要更新props
    if (sameType) {
      newFiber = {
        type: oldFiber.type,
        props: element.props,
        dom: oldFiber.dom,
        parent: wipFiber,
        base: oldFiber,
        effectTag: "UPDATE",
      };
    }
    // 类型不相同 需要创建新的dom
    if (element && !sameType) {
      newFiber = {
        type: element.type,
        props: element.props,
        dom: null,
        parent: wipFiber,
        base: null,
        effectTag: "PLACEMENT",
      };
    }
    // 类型不相同需要把老fiber给删除
    // 放入到deletions数组里
    if (oldFiber && !sameType) {
      oldFiber.effectTag = "DELETION";
      deletions.push(oldFiber);
    }
    if (oldFiber) {
      oldFiber = oldFiber.sibling;
    }
   
    if (index === 0) {
      wipFiber.child = newFiber;
    } else {
      prevSibling.sibling = newFiber;
    }
    index++;
    prevSibling = newFiber;
  }
}
```
deletions在全局声明，在render里进行初始化，提交时遍历执行commitWork
```jsx
function render(vdom, container) {
  wipRoot = {
    dom: container,
    props: {
      children: [vdom],
    },
    base: currentRoot,
  };
  deletions = [];
  nextUnitOfWork = wipRoot;
}

function wookLoop(deadline) {
  if (nextUnitOfWork && deadline.timeRemaining() > 1) {
    nextUnitOfWork = performUnitOfWork(nextUnitOfWork);
  }
  if (!nextUnitOfWork && wipRoot) {
    deletions.forEach(commitWork);
    commitWork(wipRoot);
    currentRoot = wipRoot;
    wipRoot = null;
    deletions = null;
  }
  requestIdleCallback(wookLoop);
}
```
打上标记后，需要在commitWork中根据不同的标记进行处理
PLACEMENT的直接添加到dom树中
UPDATE的需要更新props
DELETION的则进行删除操作
```jsx

function commitWork(wipFiber) {
  if (!wipFiber) {
    return;
  }
  const domParent = fiber.parent.dom;
  if (fiber.effectTag === "PLACEMENT" && fiber.dom) {
    domParent.appendChild(fiber.dom);
  } else if (fiber.effectTag === "UPDATE" && fiber.dom) {
    updateDom(fiber.dom, fiber.base.props, fiber.props);
  } else if (fiber.effectTag === "DELETION") {
    domParent.removeChild(fiber.dom);
  }

  commitWork(wipFiber.child);
  commitWork(wipFiber.sibling);
}
```
在updateDom中进行props的更新
```jsx
function updateDom(dom, prevProps, nextProps) {
  // 以 “on” 开头的属性作为事件要特别处理
  // 移除旧的或者变化了的的事件处理函数
  Object.keys(prevProps)
    .filter((key) => key.startsWith("on"))
    .filter((key) => !(key in nextProps) || prevProps[key] !== nextProps[key])
    .forEach((name) => {
      const eventType = name.toLowerCase().substring(2);
      dom.removeEventListener(eventType, prevProps[name]);
    });
  // 移除旧的属性
  Object.keys(prevProps)
    .filter((key) => key !== "children")
    .filter((key) => !key.startsWith("on"))
    .filter((key) => prevProps[key] !== nextProps[key])
    .forEach((name) => {
      dom[name] = "";
    });
  // 添加或者更新属性
  Object.keys(nextProps)
    .filter((key) => key !== "children")
    .filter((key) => !key.startsWith("on"))
    .filter((key) => prevProps[key] !== nextProps[key])
    .forEach((name) => {
      dom[name] = nextProps[name];
    });
  // 添加新的事件处理函数
  Object.keys(nextProps)
    .filter((key) => key.startsWith("on"))
    .filter((key) => prevProps[key] !== nextProps[key])
    .forEach((name) => {
      const eventType = name.toLowerCase().substring(2);
      dom.addEventListener(eventType, nextProps[name]);
    });
}
```
同时在createDom中进行逻辑的修改
```jsx
function createDom(vdom) {
  const dom =
    vdom.type === "TEXT_NODE"
      ? document.createTextNode("")
      : document.createElement(vdom.type);

  updateDom(dom, {}, fiber.props);

  return dom;
}
## 函数组件
以一个简单的函数组件为例：
```js
function App(props) {
    return createElement("h1", null, "Hellow ", props.name);
}
const element = createElement(App, { name: "world" });
render(element, document.getElementById("root"));
```
在performUnitOrWork中需要判断是否是函数组件
```jsx
function performUnitOfWork(fiber) {
  fiber.type instanceof Function
    ? updateFunctionComponent(fiber)
    : updateHostComponent(fiber);

  if (fiber.child) {
    return fiber.child;
  }

  let nextFiber = fiber;
  while (nextFiber) {
    if (nextFiber.sibling) {
      return nextFiber.sibling;
    }
    nextFiber = nextFiber.parent;
  }
  return null;
}

function updateFunctionComponent(fiber) {
  reconcileChildren(fiber, [fiber.type(fiber.props)]);
}
function updateHostComponent(fiber) {
  if (!fiber.dom) {
    fiber.dom = createDom(fiber);
  }
  reconcileChildren(fiber, fiber.props.children);
}
```
因为函数组件是没有dom节点的
且函数组件的children来自函数的返回结果
所以需要改动commitWork中的逻辑
```jsx
function commitWork(wipFiber) {
  if (!wipFiber) {
    return;
  }
  // 是函数组件时节点不存在 DOM，
  // 故需要遍历父节点以找到最近的有 DOM 的节点
  let domParentFiber = wipFiber.parent;
  while (!domParentFiber.dom) {
    domParentFiber = domParentFiber.parent;
  }
  const domParent = domParentFiber.dom;
  if (wipFiber.effectTag === "PLACEMENT" && wipFiber.dom) {
    domParent.appendChild(wipFiber.dom);
  } else if (wipFiber.effectTag === "UPDATE" && wipFiber.dom) {
    updateDom(wipFiber.dom, wipFiber.base.props, wipFiber.props);
  } else if (wipFiber.effectTag === "DELETION") {
    commitDeletion(wipFiber, domParent);
  }

  commitWork(wipFiber.child);
  commitWork(wipFiber.sibling);
}

function commitDeletion(fiber, domParent) {
    // 如果是函数组件就没有DOM 需要继续向下遍历
  if (fiber.dom) {
    domParent.removeChild(fiber.dom);
  } else {
    commitDeletion(fiber.child, domParent);
  }
}
```
## useState
案例：
```jsx
function App(props) {
    const [count, setCount] = useState(0);
    return createElement(
      "h1",
      { onClick: () => setCount((v) => v + 1) },
      "Count: ",
      count
    );
}
const element = createElement(App, {});
render(element, document.getElementById("root"));
```
全局声明wipFiber变量表示当前的fiber
hookIndex来表示当前的hook序号
在wipFIber上声明hooks数组，用来依次存放hook
在updateFunctionCompoent中进行赋值
```jsx
function updateFunctionComponent(fiber) {
  wipFiber = fiber;
  hookIndex = 0;
  wipFiber.hooks = [];
  const children = [fiber.type(fiber.props)];
  reconcileChildren(fiber, children);
}
```
useState的简单实现
```jsx
function useState(initial) {
  const oldHook = wipFiber.base?.hooks?.[hookIndex];
  const hook = {
    state: oldHook ? oldHook.state : initial,
    queue: [],
  };
  const actions = oldHook ? oldHook.queue : [];
  actions.forEach((action) => {
    // action可以是传入一个参数为state的函数
    hook.state = action instanceof Function ? action(hook.state) : action;
  });
  
  //setState将wipRoot重新赋值 触发渲染
  const setState = (action) => {
    hook.queue.push(action);
    wipRoot = {
      dom: currentRoot.dom,
      props: currentRoot.props,
      base: currentRoot,
    };
    nextUnitOfWork = wipRoot;
    deletions = [];
  };
  wipFiber.hooks.push(hook);
  hookIndex++;
  return [hook.state, setState];
}
```
## 参考链接
https://pomb.us/build-your-own-react/