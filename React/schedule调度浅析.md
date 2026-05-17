## 前言
- 众所周知，浏览器是多线程的，其中负责渲染页面的渲染线程和处理`JavaScript`程序的JS引擎线程是互斥的，如果JS代码的执行时间过长，就会造成页面渲染加载阻塞
- 浏览器通常是60hz的刷新率，也就是每16.7ms会重新渲染页面，所以`schedule`的目的就是在每一帧的空闲时间里来执行JS代码，使渲染页面等行为可以顺利进行

## 原理浅析
### priority

调度会分为不同的优先级，不同的优先级有不同的过期时间

```js
const ImmediatePriority = 1;
const NormalPriority = 2;
const LowPriority = 3;

const IMMEDIATE_PRIORITY_TIMEOUT = -1;
const NORMAL_PRIORITY_TIMEOUT = 25;
const LOW_PRIORITY_TIMEOUT = 5000;
```



### scheduleCallback

通过`scheduleCallback`方法来调度回调函数，根据参数中的优先级来计算过期时间

`taskQueue`是通过小顶堆实现的优先级队列，根据`sortIndex`来进行比较，在`push`和`pop`的时候会调整队列中的任务顺序

将需要调度的任务放到队列后，通过`requestCallback`方法开始调度

```js
const taskQueue = []

const TIMEOUT_CONFIG = {
  [ImmediatePriority]: IMMEDIATE_PRIORITY_TIMEOUT,
  [NormalPriority]: NORMAL_PRIORITY_TIMEOUT,
  [LowPriority]: LOW_PRIORITY_TIMEOUT,
};

const scheduleCallback = (callback, priority) => {
  const timeout = TIMEOUT_CONFIG[priority];
  const startTime = getCurrentTime();
  const expirationTime = startTime + timeout;
  const newTask = {
    callback,
    priority,
    startTime,
    expirationTime,
    sortIndex: expirationTime,
  };
  push(taskQueue, newTask);
  requestCallback(workLoop);
};
```

### requestCallback

在`requestCallback`中会通过`MessageChannel`来进行宏任务调度

通过`scheduledCallback`来记录`callback`参数

```js
let scheduledCallback;

const messagechannel = new MessageChannel();
const port1 = messagechannel.port1;
const port2 = messagechannel.port2;

const requestCallback = (callback) => {
  scheduledCallback = callback;
  port2.postMessage(null);
};
```

在`onmessage`的回调中，会计算出本次任务执行的截止时间

执行在`requestCallback`中设置的`callback`，也就是`workloop`方法

如果有`hasMoreWork`表示截止时间到了但是`taskQuque`中还有任务没执行完，就会在下一个宏任务中继续执行

```js
let deadline;
const yieldInterval = 5;
const shouldYield = () => {
  return getCurrentTime() >= deadline;
};

port1.onmessage = () => {
  const currentTime = getCurrentTime();
  deadline = currentTime + yieldInterval;
  const hasMoreWork = scheduledCallback(currentTime);
  if (hasMoreWork) {
    port2.postMessage(null);
  }
};
```

### workloop

通过`peek`来获取`taskQueue`中过期时间最短的任务

在循环的时候会进行判断

- 如果任务没有过期并且任务执行的截止时间到了的时候，就会跳出循环，没有执行完的任务会在下一个宏任务继续执行，即跳出循环时`currentTask`还是有值的情况

- 但是如果任务已经过期，即使截止时间已经到了，该任务也会继续执行，直至`peek`到下一个没有过期的任务

`newCallback`如果有值表示该任务执行时间到了但是还没有执行完，就会给`currentTask`的`callback`属性重新赋值，用于中断后重新启动
如果任务执行完毕就`pop`，继续`peek`获取任务来执行

```js
const workLoop = (currentTime) => {
  currentTask = peek(taskQueue);
  while (currentTask) {
    if (currentTask.expirationTime > currentTime && shouldYield()) {
      break;
    }
    const didUserCallbackTimeout = currentTask.expirationTime <= currentTime;
    const newCallback = currentTask.callback(didUserCallbackTimeout);
    if (newCallback) {
      currentTask.callback = newCallback;
    } else {
      pop(taskQueue);
      currentTask = peek(taskQueue);
    }
  }
  return currentTask;
};
```
