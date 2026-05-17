## 4.9
### satisfies操作符
TS有强大的推导能力能够自动地完成某些类型信息的推导
```ts
const palette = {
  red: [255, 0, 0],
  green: "#00ff00",
  blue: [0, 0, 255]
};

// 其类型将被自动推导为：
interface Palette {
  red: number[];
  green: string;
  blue: number[];
}
```
由于是从值推导得到类型，而不是使用类型约束值，那么在提供了错误的值时，推导得到的类型信息也将出现问题
```ts
const palette = {
  red: [255, 0, 0],
  // typo
  grren: '#00ff00',
  blue: [0, 0, 255],
};
```
为了避免这种问题，通常会使用显式地类型标注：
```ts
type Colors = 'red' | 'green' | 'blue';
type RGB = [number, number, number];

const palette: Record<Colors, string | RGB> = {
  red: [255, 0, 0],
  // × 不存在此属性
  grren: '#00ff00',
  blue: [0, 0, 255],
};
```
看起来完成了非常精确的类型标注，但现在调用出现了类型错误：
```ts
palette.green.startsWith('#'); // × 类型“string | RGB”上不存在属性“startsWith”
palette.red.startsWith('#'); // × 类型“string | RGB”上不存在属性“startsWith”
```
在进行变量类型信息地标注时，其实是在告诉 TS 类型系统，这个变量的值必须完全符合这个类型，在后续使用这个变量时其类型信息会完全使用我们提供地类型信息，而不是其推导出的类型信息，即现在是让值完全符合类型，然后使用我们提供的类型信息
而实际需要的效果则是，让值符合类型的前提下，结合使用值推导出的类型信息：palette只需要满足类型约束，其键值类型不会使用 string | RGB ，而是仍然使用每个属性访问推导出的对应类型
而satisfies就是来支持这个功能的：
```ts
const palette = {
    red: [255, 0, 0],
    green: "#00ff00",
    blue: [0, 0, 255]
} satisfies Record<Colors, string | RGB>;

// string
palette.green.startsWith('#'); // √
// [number, number, number]
palette.red.find(); // √
// [number, number, number];
palette.blue.entries(); // √
```
### 单文件级别配置
单文件级别的 tsconfig 配置，使用 @ts-config value 的形式，如以下示例：
```ts
// @ts-strict 
// @ts-noUnusedLocals
// @ts-strictNullChecks
// @ts-noPropertyAccessFromIndexSignature false
```
### 对未列出属性的类型收窄增强
在面对联合类型时，经常使用类型守卫的方式来显式地提供类型信息，来帮助修正对应分支的类型控制流分析上下文
```ts
interface LoginUser {
  userId: string;
  invitor: string;
}

interface Visitor {
  visitorId: string;
  from: string;
}

function checkUser(user: LoginUser | Visitor): string {
  if ('userId' in user) {
    return user.invitor
  } else {
    return user.from;
  }
}
```
然而 in关键字在某些时候也存在着能力的不足
```ts
interface LoginUser {
  userId: string;
  invitor: string;
}

interface Visitor {
  visitorId: string;
  from: string;
}

function checkUser(info: { user: unknown }): string {
  const user = info.user;
  if (user && typeof user === "object") {
    if ('userId' in user && typeof user.userId === 'string') {
      // Property 'userId' does not exist on type 'object'
      return user.userId; 
    }
  }
}
```
in操作符只会严格缩小到当前需要的检查类型，而 userId 并没有在 user类型上列出，所以 user 仍然只会是 object 类型
而在 4.9 版本，现在面对这种情况， in 操作符会将检查类型缩小到 object & Record<"userId", unknown> 类型，这样就能够支持未列出属性的类型守卫了
另外，4.9 版本现在也会约束 in 操作符的左侧必须是 string / number / symbol 类型，以及右侧必须是 object 类型
### 对 NaN 类型的相等检查
新增了错误使用等价判断方式的提示：
```ts
// 此表达式将始终返回 false，你是否指 Number.isNaN(value) ?
if(value === NaN) {}
```
## 4.8
### 交叉类型与联合类型的类型收窄增强
对 --strictNullChecks 进行了进一步增强，主要体现在联合类型与交叉类型，以及类型收窄地表现上
现在 unknown 和 {} | null | undefined 可以互相兼容
```ts
declare let v1: unknown;
declare let v2: {} | null | undefined;

v1 = v2;
// 此前会报错，因为认为 unknown 包含的类型信息更多
v2 = v1;
```
将使用 {} 的交叉类型，如 obj & {} 直接简化为 obj 类型，前提是 obj 并非来自于泛型，且非 null / undefined
因为交叉类型要求同时满足两个类型，而只要 obj 不是 null / undefined 类型，就可以认为必定也符合 {} 类型，因此可以直接将 {} 从交叉类型中移除：
```ts
type T1 = {} & string;  // string
type T2 = {} & 'linbudu';  // 'linbudu'
type T3 = {} & object;  // object
type T4 = {} & { x: number };  // { x: number }
type T5 = {} & null;  // never
type T6 = {} & undefined;  // never
```
NonNullable 实现会被更改为以下这种
```ts
type _NonNullable<T> = T extends null | undefined ? never : T;
type NonNullable<T> = T & {};
```
### 模板字符串类型中的 infer 提取
当 infer 被约束为一个原始类型，那么它现在会尽可能将 infer 的类型信息推导到字面量类型的级别
```ts
// 此前为 number，现在为 '100'
type SomeNum = "100" extends `${infer U extends number}` ? U : never;

// 此前为 boolean，现在为 'true'
type SomeBool = "true" extends `${infer U extends boolean}` ? U : never;
```
### 绑定类型中的类型推导
泛型填充也会受到其调用方的影响
```ts
declare function chooseRandomly<T>(x: T,): T;

// Array<string | number | boolean>
const res1 = chooseRandomly(["linbudu", 599, false]);
```
换一个方法：
```ts
declare function chooseRandomly<T>(x: T,): T;
​
// [string, number, boolean]
const [a, b, c] = chooseRandomly(["linbudu", 599, false]);
```
一泛型填充方式被称为绑定模式。而在新版本中，禁用了基于绑定模式的类型推导，因为其对泛型的影响并不始终正确
```ts
declare function f<T>(x?: T): T;
​
// [any, any, any] 你咋知道我是个数组结构？？？
const [x, y, z] = f();
```
### 对象字面量值与数组字面量值的全等比较提示
```ts
const obj = {};
​
// 此语句始终将返回 false，因为 JavaScript 中使用引用地址比较对象，而非实际值
if(obj === {}){
  
}

const func = () => {};
​
// 此表达式将始终返回 true，你是否想要调用 func ？
if(func) { }
```
## 4.7
### 计算属性的类型控制流分析
在 4.7 版本以前， typeof obj[key] === "string" 成立后的语句块中，obj[key] 的类型并不会被收窄到 string
```ts
const key = Symbol();

const numberOrString = Math.random() < 0.5 ? 42 : "hello";

let obj = {
    [key]: numberOrString,
};

if (typeof obj[key] === "string") {
    let str = obj[key].toUpperCase();
}
```
### 对象中的函数类型推导增强
这两个调用都是正常的，TypeScript 能够从 produce 函数的返回值推导出泛型参数 T 的类型，并应用到 consume 函数的入参类型中
```ts
declare function f<T>(arg: {
    produce: (n: string) => T,
    consume: (x: T) => void }
): void;

// Works
f({
    produce: () => "hello",
    consume: x => x.toLowerCase()
});

// Works
f({
    produce: (n: string) => n,
    consume: x => x.toLowerCase(),
});
```
而以下几个例子在4.7版本之前就不行了：
在第一处，produce 的入参类型并没有成功地传递给返回值类型。而在第二、第三个，produce 函数的返回值类型没有从其内部推导得到，仍然是默认的 unknown 类型
```ts
f({
    produce: n => n,
    consume: x => x.toLowerCase(),
});

f({
    produce: function () { return "hello"; },
    consume: x => x.toLowerCase(),
});

f({
    produce() { return "hello" },
    consume: x => x.toLowerCase(),
});
```
### 泛型实例化表达式
假设要创建一个键类型为 string，键值类型为 Error 的 Map，通常会这么做
```ts
const errorMap: Map<string, Error> = new Map()
```
或者将这个 Map 类型抽离为一个类型别名：
```ts
type ErrorMapType = Map<string, Error>
```
但是两种做法都是在定义时的类型参数填充，且变量的类型是在实际调用时才确认的
而使用泛型实例化表达式，可以做到无需调用的情况下预先填充类型参数：
```ts
// 注意，这里不是类型别名
const ErrorMap = Map<string, Error>;

const errorMap = new ErrorMap();
```
一个更常见的场景是对接受泛型的函数按场景进行对应的实例化
```ts
function asFEEngineer<T>(value: T) {
    return { value };
};
```
这个函数只能确定是一个前端工程师，而不能确定其具体的方向
有了实例化表达式，可以通过预填充泛型参数的方式来实现不同场景的对应实例
```ts
const asMobile = asFEEngineer<"mobile">;
const asNodeJs = asFEEngineer<"nodejs">;
const asInfra = asFEEngineer<"infra">;
```
每一个函数除了泛型参数已固定以外，和原本的函数完全一致
```ts
const mobileFEEngineer = asMobile("mobile");
```
由于实例化表达式的本质仍然是表达式，它也支持被作为 typeof 的输入
```ts
type StringBoxMaker = typeof asFEEngineer<"mobile">;  // (value: "mobile") => { value: "mobile" }
type ErrorMapConstructor = typeof Map<string, Error>;  // new () => Map<string, Error>
```
### infer 的 extends 约束支持
以提取数组/元组的首个字符串类型成员为🌰
```ts
type FirstString<T> =
    T extends [infer S, ...unknown[]]
        ? S extends string ? S : never
        : never;

 // string
type A = FirstString<[string, number, number]>;

// "hello"
type B = FirstString<["hello", number, number]>;

// "hello" | "world"
type C = FirstString<["hello" | "world", boolean]>;

// never
type D = FirstString<[boolean, number, number]>;
```
新版本支持了 infer 关键字的 extends 约束能力，这一能力能够大大简化许多现存工具类型/类型体操实现的条件语句判断
```ts
type FirstString<T> =
    T extends [infer S extends string, ...unknown[]]
        ? S
        : never;
```