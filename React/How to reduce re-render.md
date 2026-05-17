众所周知，state的变化会使React组件重新渲染
```jsx
const Change = () => {
  const [count, setCount] = useState(0);
  console.log("Change render");
  return (
    <div
      onClick={() => {
        console.log("Change click");
        setCount((c) => c + 1);
      }}
    >
      {count}
    </div>
  );
};

// Change click
// Change render
```
并且父组件的渲染会使子组件也跟着渲染，即使子组件里没有props
```jsx
const Parent = () => {
  const [count, setCount] = useState(0);
  console.log("Parent render");
  return (
    <div
      onClick={() => {
        setCount((c) => c + 1);
      }}
    >
      {count}
      <Child />
    </div>
  );
};

const Child = () => {
  console.log("Child render");
  return <div>Child</div>;
};

// Parent render
// Child render
```
React提供了memo和useMemo的方法
> 但memo和useMemo本身也是有消耗的，不要太高估组件re-render的成本，对于props很多但是没有很多子组件的组件来说，检查props带来的成本可能更高
```jsx
// memo
const Parent = () => {
  const [count, setCount] = useState(0);
  console.log("Parent render");
  return (
    <div
      onClick={() => {
        setCount((c) => c + 1);
      }}
    >
      {count}
      <Child />
    </div>
  );
};

const Child = memo(() => {
  console.log("Child render");
  return <div>Child</div>;
});

// or useMemo
const Parent = () => {
  const [count, setCount] = useState(0);
  const memoComponent = useMemo(() => <Child />, []);
  console.log("Parent render");
  return (
    <div
      onClick={() => {
        setCount((c) => c + 1);
      }}
    >
      <>
        {count}
        {memoComponent}
      </>
    </div>
  );
};

const Child = () => {
  console.log("Child render");
  return <div>Child</div>;
};

// only Parent render
```
memo默认会浅比较props，如果没有发生变化则会bailout
```jsx
function memo<Props>(
  type: React$ElementType,
  compare?: (oldProps: Props, newProps: Props) => boolean,
) {
  const elementType = {
    $$typeof: REACT_MEMO_TYPE,
    type,
    compare: compare === undefined ? null : compare,
  };
  return elementType;
}

function updateMemoComponent(
  current: Fiber | null,
  workInProgress: Fiber,
  Component: any,
  nextProps: any,
  updateLanes: Lanes,
  renderLanes: Lanes,
): null | Fiber {
 //...
   const prevProps = currentChild.memoizedProps;
   let compare = Component.compare;
   compare = compare !== null ? compare : shallowEqual;
   if (compare(prevProps, nextProps) && current.ref === workInProgress.ref) {
     return bailoutOnAlreadyFinishedWork(current, workInProgress, renderLanes);
   }
 //...
}

function bailoutOnAlreadyFinishedWork(
  current: Fiber | null,
  workInProgress: Fiber,
  renderLanes: Lanes,
): Fiber | null {
  //...
  cloneChildFibers(current, workInProgress);
  return workInProgress.child;
}
```
useMemo也是同理，如果依赖项没有发生变化，则会返回之前缓存的内容
```jsx
function useMemo<T>(nextCreate: () => T, deps: Array<mixed> | void | null): T {
  // ...
  const nextDeps = deps === undefined ? null : deps;
  const prevState = workInProgressHook.memoizedState;
  if (prevState !== null) {
    if (nextDeps !== null) {
      const prevDeps = prevState[1];
      if (areHookInputsEqual(nextDeps, prevDeps)) {
        return prevState[0];
      }
    }
  }
  const nextValue = nextCreate();
  workInProgressHook.memoizedState = [nextValue, nextDeps];
  return nextValue;
}
```
还可以将状态往下移，将re-render保持在更小的范围里
```jsx
// old
const Parent = () => {
  const [boyAge, setBoyAge] = useState(0);
  console.log("Parent render");
  return (
    <div
      onClick={() => {
        setBoyAge((c) => c + 1);
      }}
    >
      <>
        <Boy boyAge={boyAge} />
        <Girl />
      </>
    </div>
  );
};

const Boy = ({ boyAge }) => {
  console.log("Boy render");
  return <div>Boy {boyAge}</div>;
};

const Girl = () => {
  console.log("Girl render");
  return <div>Girl</div>;
};

//Parent render
//Boy render
//Girl render

// new
const Parent = () => {
  console.log("Parent render");
  return (
    <>
      <Boy />
      <Girl />
    </>
  );
};

const Boy = () => {
  const [boyAge, setBoyAge] = useState(0);
  console.log("Boy render");
  return (
    <div
      onClick={() => {
        setBoyAge((c) => c + 1);
      }}
    >
      Boy {boyAge}
    </div>
  );
};

const Girl = () => {
  console.log("Girl render");
  return <div>Girl</div>;
};

// only Boy render
```
或者把内容往上提，把可变的部分拆分到父级组件里
Parent重新渲染了，但是从App中获取的props.children是相同的，所以React不会访问这个子树。除了使用props.children，其他的props属性也是可以的
```jsx
const Parent = ({ children }) => {
  const [count, setCount] = useState(0);
  console.log("Parent render");
  return (
    <div onClick={() => setCount((c) => c + 1)}>
      {children}
      {count}
    </div>
  );
};

const Child = () => {
  console.log("Child render");
  return <div>Child</div>;
};

const App = () => (
  <Parent>
    <Child />
  </Parent>
);

// only Parent render
```