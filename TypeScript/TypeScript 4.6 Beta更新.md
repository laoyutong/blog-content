## 允许在constructors的super前写代码

在JavaScript的类中引用`this`之前必须先调用`super`，TypeScript中也强制这点，但是更加严格，如果具有任何属性初始化的类在`constructor`的开头包含任何代码都会报错

```js
class Base { }

class Derived extends Base {
  constructor() {
    console.log('123') // A 'super' call must be the first statement in the constructor when a class contains initialized properties, parameter properties, or private identifiers
    super();
  }
}
```

新版本在检查方面变得宽松，可以让其他的代码在`super`之前执行，但是仍然会确保`super`会出现在引用`this`之前

如果在`super`前引用了`this`，会产生如下报错

```javascript
// A 'super' call must be the first statement in the constructor to refer to 'super' or 'this' when a derived class contains initialized properties, parameter properties, or private identifiers.(2376)
//'super' must be called before accessing 'this' in the constructor of a derived class.(17009)
```

## 改进递归深度检查

对象类型的兼容基于它拥有的成员

```typescript
interface Source {
    prop: string;
}

interface Target {
    prop: number;
}

function check(source: Source, target: Target) {
    target = source;
    // error!
    // Type 'Source' is not assignable to type 'Target'.
    //   Types of property 'prop' are incompatible.
    //     Type 'string' is not assignable to type 'number'.
}
```

TypeScript中如果一个类型遇到一定的深度检查后似乎是无限拓展的，那就认为这些类型可能是兼容的

```typescript
interface Source<T> {
    prop: Source<Source<T>>;
}

interface Target<T> {
    prop: Target<Target<T>>;
}

function check(source: Source<string>, target: Target<number>) {
    target = source;
}
```

通常情况是足够了，但是会有漏网之鱼：

因为y的嵌套比x要少，所以赋值操作应该是不成立的，但是在老的版本是不会报错的

新版本进一步提升了递归类型检查的能力，能够区分这里的两种情况，对于无限嵌套可以更加迅速地判断出来

```typescript
interface Foo<T> {
    prop: T;
}

declare let x: Foo<Foo<Foo<Foo<Foo<Foo<string>>>>>>;
declare let y: Foo<Foo<Foo<Foo<Foo<string>>>>>;

x = y;
```

## 索引访问的推断改进

新版本的TypeScript可以正确推断出这些立即索引到一个映射对象类型的索引访问类型

TypeScript理解`record.f(record.v)`的调用是有效的，而之前的版本会报错，需要通过类型断言等方式来进行有效调用

```typescript
 interface TypeMap {
    "number": number;
    "string": string;
    "boolean": boolean;
}

type UnionRecord<P extends keyof TypeMap> = { [K in P]:
    {
        kind: K;
        v: TypeMap[K];
        f: (p: TypeMap[K]) => void;
    }
}[P];

function processRecord<K extends keyof TypeMap>(record: UnionRecord<K>) {
    record.f(record.v);
}

processRecord({
    kind: "string",
    v: "hello!",
    // 'val' used to implicitly have the type 'string | number | boolean',
    // but now is correctly inferred to just 'string'.
    f: val => {
        console.log(val.toUpperCase());
    }
})
```

## 相关参数的控制流分析

当`kind`为`a`的时候，`paload`的类型应该是`number`，当`kind`为`b`的时候，`padyload`的类型应该是`string`

现在TypeScript可以缩小依赖于其他参数的参数类型

```typescript
type Func = (...args: ["a", number] | ["b", string]) => void;

const f1: Func = (kind, payload) => {
    if (kind === "a") {
        payload.toFixed();  // 'payload' narrowed to 'number'
    }
    if (kind === "b") {
        payload.toUpperCase();  // 'payload' narrowed to 'string'
    }
};

f1("a", 42);
f1("b", "hello");
```

## TypeScript追踪分析

TypeScript有一个`--generateTrace`选项来帮助识别一些耗时的类型编译工作，但是在现有的可视化工具中还是很难阅读

发布了`@typescript/analyze-trace`的工具来更容易理解这些信息，可以帮助分析TypeScript的构建性能问题

##  通用对象的解构会删除一些无法传播的成员

现在通过`...rest`来解构通用对象的时候，会删除不可解构的值以及对象中的方法

在新版本中，`rest`的类型是`Omit<T,"someProperty"|"someMethod">`

```typescript
class Thing {
    someProperty = 42;
    someMethod() {
        // ...
    }
}

function foo<T extends Thing>(x: T) {
    let { someProperty, ...rest } = x;

    // Used to work, is now an error!
    // Property 'someMethod' does not exist on type 'Omit<T, "someProperty" | "someMethod">'.
    rest.someMethod();
}
```

