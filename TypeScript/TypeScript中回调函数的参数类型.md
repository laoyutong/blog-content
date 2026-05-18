## 现象

声明三个 `inferface` , 其中`Worker` 是 `Person` 的子类型， `Programmer` 是 `Worker` 的子类型

同时声明一个函数 `main`，参数是一个入参和出参类型都是 `Worker`的函数

```jsx
interface Person {
  breath: () => void
}

interface Worker extends Person {
  work: () => void
}

interface Programmer extends Worker {
  code: () => void
}

const main = (callback: (args: Worker) => Worker) => { }

const test = (arg: Worker): Worker => {
  return arg
}

main(test)
```

如果传入的函数入参和出参类型都是 `Worker`，肯定是能通过类型校验的

但如果尝试一下修改入参和出参的类型，会发现：

入参是 `Person` ，而出参是 `Programmer` 的时候，类型校验也是可以通过的

即函数的入参可以是父类型，而出参则可以是子类型

## 原因

在入参的类型中，本质的问题是：如果 `main` 函数内调用 `callback`传入了 `Worker`，在 `test` 函数中使用的时候会不会有问题
如果 `test` 的参数类型是 `Person` ，调用 `breath` 方法，而 `Worker` 上是包含的，所以是不会有问题
反而如果`test` 的参数类型是 `Programmer` ，调用了 `code` 方法，但 `Worker` 上没有这个方法，就会产生错误



在出参的类型中，问题也是类似的：通过调用 `callback` 产生的返回值，在其上调用 `Worker` 的方法会不会有问题
很显然出参的类型必须包含 `Worker` 上的所有方法，假设在 `main` 函数中，通过 `callback` 函数生成的对象，调用了 `breath` 或者 `work` 方法，如果该对象的类型是 `Person` 则是没有 `work` 方法的，就会产生报错，而 `Programmer` 则包含了 `Worker` 上的所有方法，是不会有问题的