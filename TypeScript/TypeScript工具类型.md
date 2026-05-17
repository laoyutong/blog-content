## Partial<Type>
将一个类型的全部属性设置成可选的
```ts
interface Todo {
  title: string;
  description: string;
}
 
function updateTodo(todo: Todo, fieldsToUpdate: Partial<Todo>) {
  return { ...todo, ...fieldsToUpdate };
}
 
const todo1 = {
  title: "organize desk",
  description: "clear clutter",
};
 
const todo2 = updateTodo(todo1, {
  description: "throw out trash",
});
```
**原理**
```ts
type Partial<T> = {
    [P in keyof T]?: T[P];
};
```
## Required<Type>
和`Partial`相反，将类型的所有属性设置成必选的
```ts
interface Props {
  a?: number;
  b?: string;
}
const obj: Props = { a: 5 };
const obj2: Required<Props> = { a: 5 };
// Property 'b' is missing in type '{ a: number; }' but required in type 'Required<Props>'.
```
**原理**
```ts
type Required<T> = {
    [P in keyof T]-?: T[P];
};
```

## Readonly<Type>
将类型的所有属性设置成只读的，不能进行访问
```ts
interface Todo {
  title: string;
}
const todo: Readonly<Todo> = {
  title: "Delete inactive users",
};
todo.title = "Hello";
// Cannot assign to 'title' because it is a read-only property.
```
**原理**
```ts
type Readonly<T> = {
    readonly [P in keyof T]: T[P];
};
```
## Record<Keys, Type>
构建一个对象类型，键的类型是`Keys`，值的类型是`Type`
可以将一个类型的属性映射到另外一个类型
```ts
interface CatInfo {
  age: number;
  breed: string;
}
type CatName = "miffy" | "boris" | "mordred";
const cats: Record<CatName, CatInfo> = {
  miffy: { age: 10, breed: "Persian" },
  boris: { age: 5, breed: "Maine Coon" },
  mordred: { age: 16, breed: "British Shorthair" },
};
```
**原理**
```ts
type Record<K extends keyof any, T> = {
    [P in K]: T;
};
```
## Exclude<UnionType, ExcludedMembers>
从`UnionType`中排除可以分配给`ExcludedMembers`的成员来构造类型
```ts
type T0 = Exclude<"a" | "b" | "c", "a">;
// type T0 = "b" | "c"
type T1 = Exclude<"a" | "b" | "c", "a" | "b">;
// type T1 = "c"
type T2 = Exclude<string | number | (() => void), Function>;
// type T2 = string | number
```
**原理**
```ts
type Exclude<T, U> = T extends U ? never : T;
```

## Extract<Type, Union>
和`Exclude`相反，是从`Type`中提取可以分配给`Union`的成员来构造类型
```ts
type T0 = Extract<"a" | "b" | "c", "a" | "f">;  
// type T0 = "a"
type T1 = Extract<string | number | (() => void), Function>;    
// type T1 = () => void
```
**原理**
```ts
type Extract<T, U> = T extends U ? T : never;
```

## Pick<Type, Keys>
从`Type`中选取属性集合`Keys`来构造一个类型
```ts
interface Todo {
  title: string;
  description: string;
  completed: boolean;
}
type TodoPreview = Pick<Todo, "title" | "completed">;
const todo: TodoPreview = {
  title: "Clean room",
  completed: false,
};

```
**原理**
```ts
type Pick<T, K extends keyof T> = {
    [P in K]: T[P];
};
```
## Omit<Type, Keys>
`Omit`与`Pick`相反，是删除`keys`来构造一个属性
```ts
interface Todo {
  title: string;
  description: string;
  completed: boolean;
  createdAt: number;
}
type TodoPreview = Omit<Todo, "description">;
const todo: TodoPreview = {
  title: "Clean room",
  completed: false,
  createdAt: 1615544252770,
};
```
 **原理**
```ts
type Omit<T, K extends keyof any> = Pick<T, Exclude<keyof T, K>>;
```

## NonNullable<Type>
去除类型中的`null`和`undefined`
```ts
type T0 = NonNullable<string | number | undefined>;
// type T0 = string | number
type T1 = NonNullable<string[] | null | undefined>;
// type T1 = string[]
```
**原理**
```ts
type NonNullable<T> = T extends null | undefined ? never : T;
```

## Parameters<Type>
获取函数类型`Type`的参数来构造一个元祖类型
```ts
declare function f1(arg: { a: number; b: string }): void;
type T0 = Parameters<() => string>;
// type T0 = []
```
**原理**
```ts
type Parameters<T extends (...args: any) => any> = T extends (...args: infer P) => any ? P : never;
```

## ConstructorParameters<Type>
从构造函数的类型中构造一个元组或数组类型
```ts
type T2 = ConstructorParameters<RegExpConstructor>;
// type T2 = [pattern: string | RegExp, flags?: string]
```
**原理**
```ts
type ConstructorParameters<T extends abstract new (...args: any) => any> = T extends abstract new (...args: infer P) => any ? P : never;
```

## ReturnType<Type>
构建一个由函数Type的返回类型组成的类型
```ts
declare function f1(): { a: number; b: string };
type T0 = ReturnType<() => string>;
//  type T0 = string
```
**原理**
```ts
type ReturnType<T extends (...args: any) => any> = T extends (...args: any) => infer R ? R : any;
```