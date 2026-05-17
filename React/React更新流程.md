## 触发更新
创建一个用于保存更新状态相关信息的对象Update，包含action（新的状态或更新函数）、lane（更新的优先级）和next（多个更新会被串联成链表），会放到对应fiber节点的updateQueue上

更新发生在具体的组件上，但调度是从根节点开始的
执行`markUpdateLaneFromFiberToRoot`，从当前需要更新的fiber节点开始，根据父节点指针不断向上遍历直至root节点，并将更新优先级fiber.lane存入这一向上路径上所有祖先节点的childLanes中
childLanes字段在后续的render阶段遍历fiber树时用于判断子树中是否存在更新的依据

执行`ensureRootIsScheduled`
时机：新的更新产生、一个任务执行中途停止、执行完毕时
具体逻辑：
1. `getNextLanes`获取当前最高优先级
2. 检查现有任务
- 优先级相同：直接复用，自动批处理的关键
- 优先级更高：取消旧任务，继续向下执行，准备开启高优先级的任务
- 优先级更低：同样直接返回。高优先级的跑完后会再次触发`ensureRootIsScheduled`
3. 选择调度通道
- 同步线路：click、focus等离散事件后开启`flushSync`，放到微任务队列
- 并发线路：scroll、drag等连续事件或fetch、setTImeout等非交互式触发，会进入scheduler的时间分片流程，可以被中断

## render阶段
根据最新的state和props在内存中构建一颗新的fiber树，计算最小的DOM变更量

### 递
从rootFiber开始向下深度优先遍历，为遍历到的每个Fiber节点调用beginWork 方法。
该方法会根据传入的Fiber节点创建子Fiber节点，并将这两个Fiber节点连接起来。
当遍历到叶子节点（即没有子组件的组件）时就会进入“归”阶段。

### 归
在“归”阶段会调用completeWork处理Fiber节点。
当某个Fiber节点执行完completeWork，如果其存在兄弟Fiber节点（即fiber.sibling !== null），会进入其兄弟Fiber的“递”阶段。
如果不存在兄弟Fiber，会进入父级Fiber的“归”阶段。
```js
function App() {
  return (
    <div>
      i am
      <span>KaSong</span>
    </div>
  );
}

// rootFiber beginWork
// App Fiber beginWork
// div Fiber beginWork
// "i am" Fiber beginWork
// "i am" Fiber completeWork
// span Fiber beginWork
// span Fiber completeWork
// div Fiber completeWork
// App Fiber completeWork
// rootFiber completeWork
// 针对只有单一文本子节点的Fiber，React会特殊处理。
```
### beginWork
- mount阶段
会根据fiber.tag不同，创建不同类型的子Fiber节点

- update阶段
```js
if(current !== null) {
    const oldProps = current.memoizedProps;
     const newProps = workInProgress.pendingProps;
    
    if(oldProps !== newProps || hasLegacyContextChanges()) {
        didReceiveUpdate = true;
    } else if(!includesSomeLane(renderLanes, updateLanes)) {
        // 当前fiber.lanes优先级不够
        didReceiveUpdate = false;
        ...
        return bailoutOnAlreadyFinishedWork(current, workInProgress, renderLanes);
    } else {
        didReceiveUpdate = false;
    }
} else {
    didReceiveUpdate = false;
}
  
switch(workInProgress.tag) {
            ...
    case FunctionComponent:
        return updateFunctionComponent(...);
          case ClassComponent:
              return updateClassComponent(...);
    case MemoComponent:
        return updateMemoComponent(...);
    ...
}
```
  1. 判断oldProps === newProps （memo等方式缓存），**如果有变动则无法复用current**
  2. 当前fiber的更新优先级与此次fiber树的更新优先级判断，如果不存在更新或优先级不够，则执行`bailoutOnAlreadyFinishedWork`来复用fiber
```js
// bailoutOnAlreadyFinishedWork会判断当前fiber节点的childLanes是否在本次更新的优先级信息renderLanes中
// 如果不是，则说明workInProgress的整棵子树中都不存在更新，所以直接返回null
// 如果是，则子树中存在更新，但是当前的fiber节点是可以复用的
function bailoutOnAlreadyFinishedWork(
  current: Fiber | null,
  workInProgress: Fiber,
  renderLanes: Lanes,
): Fiber | null {
      // ...
      if (!includesSomeLane(renderLanes, workInProgress.childLanes)) {
        return null;
      } else {
        cloneChildFibers(current, workInProgress);
        return workInProgress.child;
      }
  }
```
  3.  尝试命中优化手段
  - Class组件的shouldComponentUpdate，可以跳过则执行bailoutOnAlreadyFinishedWork
  - Function组件 
```js
function updateFunctionComponent(
  current,
  workInProgress,
  Component,
  nextProps: any,
  renderLanes
) {
      // 初始化hooks链表指针、执行函数主体返回ReactElement
      nextChildren = renderWithHooks();    
      
      // 如果存在待处理的hook更新，也会设置didReceiveUpdate
      if (current !== null && !didReceiveUpdate) {
        bailoutHooks(current, workInProgress, renderLanes);        
        return bailoutOnAlreadyFinishedWork(current, workInProgress, renderLanes);
      }
     
      // 创建并返回下一个fiber节点
      reconcileChildren(current, workInProgress, nextChildren, renderLanes);
      return workInProgress.child;
}

function bailoutHooks(
  current: Fiber,
  workInProgress: Fiber,
  lanes: Lanes,
) {
  workInProgress.updateQueue = current.updateQueue;
  workInProgress.effectTag &= ~(PassiveEffect | UpdateEffect);
  current.lanes = removeLanes(current.lanes, lanes);
}
```
  4.   没有命中优化手段，则执行`reconcileChildren`，标记effectTag

### completeWork
- mount：为Fiber节点生成对应的DOM节点、将子孙DOM节点插入刚生成的DOM节点中、处理props。
- update：只是做了事件监听的注册和属性的预处理，赋值到fiber节点的updateQueue上，在commit阶段才会真正应用。

每个执行完completeWork且存在effectTag的Fiber节点会被保存在一条被称为effectList的单向链表中。

## commit阶段

### 准备阶段
触发useEffect回调与其他同步任务，由于这些任务可能触发新的渲染，所以这里要一直遍历执行直到没有任务
**主要是清理上一次渲染产生的回调任务**（🌰：微任务 or useLayoutEffect里触发更新）

### beforeMutation
1. 处理DOM节点渲染/删除后的 autoFocus、blur 逻辑。
2. 调用getSnapshotBeforeUpdate生命周期钩子。
3. 调度useEffect，异步执行的原因主要是防止同步执行时阻塞浏览器渲染

### mutation（执行dom操作）
遍历effectList，执行函数
- Placement effect：调用`parentNode.insertBefore`或`parentNode.appendChild`执行DOM插入操作
- Update effect：处理 updateQueue
  - FunctionComponent mutation：执行所有useLayoutEffect hook的销毁函数 
  - HostComponent mutation：updateQueue对应的内容渲染在页面上（处理props）
- Deletion effect：卸载不需要的节点，触发`componentWillUnmount`和`useLayoutEffect`的销毁函数

执行workInProgress到current的切换

### layout
DOM已更新完毕，但浏览器还没有重绘，但此时 JS 已经可以获取到新的DOM
- 同步执行`useLayoutEffect`的回调、执行setState的回调
- 执行生命周期：`componentDidMount`或`componentDidUpdate`
- 绑定ref，将真实的DOM实例赋值