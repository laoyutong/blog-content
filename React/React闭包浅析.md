🌰：
```js
const cache = {};
let prevValue;

const something = (value) => {
  // 检查值是否改变
  if (!cache.current || value !== prevValue) {
    cache.current = () => {
      console.log(value);
    };
  }

  // 更新它
  prevValue = value;
  return cache.current;
};

const first = something('first');
const anotherFirst = something('first');
const second = something('second');

first(); // 打印 "first"
second(); // 打印 "second"
console.log(first === anotherFirst); // 返回 true
```
每次使用 useCallback 时，都会创建一个闭包，并且我们传递给它的函数会被缓存
```js
const Component = () => {
  const [state, setState] = useState();

  const onClick = useCallback(() => {
    // state 将永远都是初始值
    // 闭包永远不会刷新
    console.log(state);

    // 忘记写依赖数组
  }, []);
};
```
**解决方案：**
使用useRef缓存
```js
const [value, setValue] = useState();
const ref = useRef();

useEffect(() => {
  ref.current = () => {
    // 最新的值
    console.log(value);
  };
});

const onClick = useCallback(() => {
  // 最新的值
  ref.current?.();
}, []);
```