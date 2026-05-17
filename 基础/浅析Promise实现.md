# 浅析Promise实现
`Promise`构造函数的参数`executor`方法是同步执行的

`then`的回调会异步执行，实际会被放置到微任务队列中，并在执行完一个宏任务后清空队列，所以会比`setTimeout`的回调优先执行
```js
class Promise {
  constructor(executor) {
    this.value = undefined;
    this.reason = undefined;
    this.status = "pending";

    const resolve = (value) => {
        this.status = "fulfilled";
        this.value = value;
    };

    const reject = (reason) => {
        this.status = "rejected";
        this.reason = reason;
    };

    try {
      executor(resolve, reject);
    } catch (e) {
      reject(e);
    }
  }
  
  then(thenable, catchable) {
    if (this.status === 'fulfilled') {
      	// 模拟异步
        setTimeout(() => {
            thenable(this.value);
        });
    }

    if (this.status === 'rejected') {
        setTimeout(() => {
          catchable(this.reason);
        });
    }
  }
}
```
`Promise`支持链式调用，所以`then`其实返回的是一个`Promise`实例

如果`then`的回调函数返回值是一个`Promise`实例，则会执行其`then`方法

其他情况则直接把返回值给`resolve`掉
```js
class Promise {
  // ...
  then(thenable) {
     return new MyPromise((resolve, reject) => {
       setTimeout(() => {
           try {
              const result = thenable(this.data);
              if (result instanceof Promise) {
                  result.then(d => {
                      resolve(d)
                  }, err => {
                      reject(err);
                  })
              }
              else {
                  resolve(result);
              }
          }
          catch (err) {
              reject(err);
          }
        });
    })
  }
}
```
`Promise`的`resolve`可能异步执行的，且一个`Promise`实例可以调用多次`then`方法：
```js
const promise = new Promise((resolve) => {
  setTimeout(() => {
    resolve(1);
  }, 1000);
});
promise.then((res) => console.log(res));
promise.then((res) => console.log(res));
```
所以`then`函数中需要根据状态来判断是否被`resolve`或者`reject`

可以通过一个数组来存储相应的回调函数，在改变状态的时候依次执行
```js
class Promise {
  constructor(executor) {
    this.status = "pending";
    this.thenables = [];
    this.value = undefined;

    const resolve = data => {
      	this.status = 'fulfilled';
        this.value = data;
        thenables.forEach(fn => fn(data));
    }
    // ...
	}
  then(thenable){
    if (this.status === 'fulfilled') {
       // ...
    }
    else {
        this.thenables.push(thenable);
    }
  }
}
```
最终完整实现版本：
```js

const PENDING = "pending",
RESOLVED = "resolved",
REJECTED = "rejected"

class MyPromise {
changeStatus(newStatus, newValue, queue) {
    if (this.status !== PENDING) {
        return;
    }
    this.status = newStatus;
    this.value = newValue;
    queue.forEach(handler => handler(newValue));
}

constructor(executor) {
    this.status = PENDING;
    this.value = undefined;
    this.thenables = [];
    this.catchables = [];

    const resolve = data => {
        this.changeStatus(RESOLVED, data, this.thenables);
    }

    const reject = reason => {
        this.changeStatus(REJECTED, reason, this.catchables);
    }
    try {
        executor(resolve, reject)
    }
    catch (err) {
        reject(err);
    }
}

settleHandle(handler, immediatelyStatus, queue) {
    if (typeof handler !== "function") {
        return;
    }
    if (this.status === immediatelyStatus) {
        setTimeout(() => {
            handler(this.value);
        }, 0);
    }
    else {
        queue.push(handler);
    }
}

linkPromise(thenalbe, catchable) {
    function exec(data, handler, resolve, reject) {
        try {
            const result = handler(data);
            if (result instanceof MyPromise) {
                result.then(d => {
                    resolve(d)
                }, err => {
                    reject(err);
                })
            }
            else {
                resolve(result);
            }
        }
        catch (err) {
            reject(err);
        }
    }

    return new MyPromise((resolve, reject) => {
        this.settleHandle(data => {
            exec(data, thenalbe, resolve, reject);
        }, RESOLVED, this.thenables)

        this.settleHandle(reason => {
            exec(reason, catchable, resolve, reject);
        }, REJECTED, this.catchables)
    })
}

then(thenable, catchable) {
    return this.linkPromise(thenable, catchable);
}

catch(catchable) {

    return this.linkPromise(undefined, catchable);
}


static all(proms) {
    return new Promise((resolve, reject) => {
        const results = proms.map(p => {
            const obj = {
                result: undefined,
                isResolved: false
            }
            p.then(data => {
                obj.result = data;
                obj.isResolved = true;
                const unResolved = results.filter(r => !r.isResolved)
                if (unResolved.length === 0) {
                    resolve(results.map(r => r.result));
                }
            }, reason => {
                reject(reason);
            })
            return obj;
        })
    })
}

static race(proms) {
    return new Promise((resolve, reject) => {
        proms.forEach(p => {
            p.then(data => {
                resolve(data);
            }, err => {
                reject(err);
            })
        })
    })
}

static resolve(data) {
    if (data instanceof MyPromise) {
        return data;
    }
    else {
        return new MyPromise(resolve => {
            resolve(data);
        })
    }
}

static reject(reason) {
    return new MyPromise((_resolve, reject) => {
        reject(reason);
    })
}
}

```