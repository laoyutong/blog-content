# React Router v6 浅析
## 新特性
### 路由组件
`Switch`重命名为`Routes`
`component`和`render`被`element`替代,便于参数的传递
```js
<Routes>
      <Route path="/" element={<Home />} />
      <Route path="/user" element={<User />} />
      <Route path="/profile" element={<Profile />} />
</Routes>
```
`Redirect`被删除，可以通过`Navigate`来替代
```js
<Routes>
    <Route path='/login' element={<Login/>}/>
    <Route path='/admin' element={<Admin/>}/>
    <Route path="*" element={<Navigate to="/login" />} />
</Routes>
```
### 嵌套路由
`Route`的`children`可以接受子路由
`path`支持相对路径
`index`是默认子路由，称为索引路由
```js
<Routes>
  <Route path="/" element={<Layout />}>
    <Route index element={<Activity />} />
    <Route path="invoices" element={<Invoices />} />
    <Route path="activity" element={<Activity />} />
  </Route>
</Routes>
```
使用`Outlet`来渲染子路由元素
```js
function Layout() {
  return (
    <div>
      <h1>Layout</h1>
      <Outlet />
    </div>
  );
}
```
### Hook
移除`useHistory`
`useNavigate`返回一个函数，该函数可以以编程方式进行导航
```js
import { useNavigate } from "react-router-dom";

function SignupForm() {
  let navigate = useNavigate();
  async function handleSubmit(event) {
    await submitForm(event.target);
    navigate("../success", { replace: true });
  }
  return <form onSubmit={handleSubmit}>{/* ... */}</form>;
}
```
`useRoutes`可以替代`react-router-config`
```js
import { useRoutes } from "react-router-dom";
function App() {
  let element = useRoutes([
    {
      path: "/",
      element: <Dashboard />,
      children: [
        {
          path: "messages",
          element: <DashboardMessages />
        },
        { path: "tasks", element: <DashboardTasks /> }
      ]
    },
    { path: "team", element: <AboutPage /> }
  ]);
  return element;
}
```
### 匹配规则
`/teams/new`的URL两个Route的path都可以匹配上
但是`teams/new`比`/teams/:teamId`更加具体，所以会渲染`NewTeamForm`
```js
<Route path="teams/:teamId" element={<Team />} />
<Route path="teams/new" element={<NewTeamForm />} />
```
## 原理解析
### BrowserRouter
创建`history`对象，通过`listen`方法监听，如果路由发生变化则重新渲染
```js
export function BrowserRouter({
  basename,
  children,
  window
}: BrowserRouterProps) {
  let historyRef = React.useRef<BrowserHistory>();
  if (historyRef.current == null) {
    historyRef.current = createBrowserHistory({ window });
  }

  let history = historyRef.current;
  let [state, setState] = React.useState({
    action: history.action,
    location: history.location
  });

  React.useLayoutEffect(() => history.listen(setState), [history]);

  return (
    <Router
      basename={basename}
      children={children}
      location={state.location}
      navigationType={state.action}
      navigator={history}
    />
  );
}
```
### Router
创建`NavigationContext`和`LocationContext`，对路径进行一些转换
```js
export function Router({
  basename: basenameProp = "/",
  children = null,
  location: locationProp,
  navigationType = NavigationType.Pop,
  navigator,
  static: staticProp = false
}: RouterProps): React.ReactElement | null {
  //  '////abc' => '/abc'
  let basename = normalizePathname(basenameProp);
  
  let navigationContext = React.useMemo(
    () => ({ basename, navigator, static: staticProp }),
    [basename, navigator, staticProp]
  );

  let {
    pathname = "/",
    search = "",
    hash = "",
    state = null,
    key = "default"
  } = locationProp;

  let location = React.useMemo(() => {
     // ('/abc/def','/abc') => '/def'
    let trailingPathname = stripBasename(pathname, basename);
    if (trailingPathname == null) {
      return null;
    }
    return {
      pathname: trailingPathname,
      search,
      hash,
      state,
      key
    };
  }, [basename, pathname, search, hash, state, key]);

  return (
    <NavigationContext.Provider value={navigationContext}>
      <LocationContext.Provider
        children={children}
        value={{ location, navigationType }}
      />
    </NavigationContext.Provider>
  );
}
```
### Routes
`Route`组件必须包裹在`Routes`中，不会直接渲染
```js
export function Route(
  _props: PathRouteProps | LayoutRouteProps | IndexRouteProps
): React.ReactElement | null {
  invariant(
    false,
    `A <Route> is only ever to be used as the child of <Routes> element, ` +
      `never rendered directly. Please wrap your <Route> in a <Routes>.`
  );
}
```
`Routes`通过`useRoutes`来实现
```js
export function Routes({
  children,
  location
}: RoutesProps): React.ReactElement | null {
  return useRoutes(createRoutesFromChildren(children), location);
}
```
通过`createRoutesFromChildren`来处理`children`，变成配置的形式
```js
export function createRoutesFromChildren(
  children: React.ReactNode
): RouteObject[] {
  let routes: RouteObject[] = [];

  React.Children.forEach(children, element => {
    if (!React.isValidElement(element)) {
      // Ignore non-elements. This allows people to more easily inline
      // conditionals in their route config.
      return;
    }

    if (element.type === React.Fragment) {
      // Transparently support React.Fragment and its children.
      routes.push.apply(
        routes,
        createRoutesFromChildren(element.props.children)
      );
      return;
    }

    invariant(
      element.type === Route,
      `[${
        typeof element.type === "string" ? element.type : element.type.name
      }] is not a <Route> component. All component children of <Routes> must be a <Route> or <React.Fragment>`
    );

    let route: RouteObject = {
      caseSensitive: element.props.caseSensitive,
      element: element.props.element,
      index: element.props.index,
      path: element.props.path
    };

    if (element.props.children) {
      route.children = createRoutesFromChildren(element.props.children);
    }

    routes.push(route);
  });

  return routes;
}
```
`useRoutes`会渲染匹配的`element`
`matchRoutes`会根据传入的路由配置和`pathname`获得匹配的数据
如果`matches`的长度大于1，表示有子路由存在
```js
export function useRoutes(
  routes: RouteObject[],
  locationArg?: Partial<Location> | string
): React.ReactElement | null {

  // 必须在 Router 的上下文中使用
  invariant(
    useInRouterContext(),
    // TODO: This error is probably because they somehow have 2 versions of the
    // router loaded. We can help them understand how to avoid that.
    `useRoutes() may be used only in the context of a <Router> component.`
  );
  
  // ……
  // 获取各种参数ing
  // ……
  
  let pathname = location.pathname || "/";
  let remainingPathname =
    parentPathnameBase === "/"
      ? pathname
      : pathname.slice(parentPathnameBase.length) || "/";

  let matches = matchRoutes(routes, { pathname: remainingPathname });
  
  return _renderMatches(
    matches &&
      matches.map(match =>
        Object.assign({}, match, {
          params: Object.assign({}, parentParams, match.params),
          pathname: joinPaths([parentPathnameBase, match.pathname]),
          pathnameBase:
            match.pathnameBase === "/"
              ? parentPathnameBase
              : joinPaths([parentPathnameBase, match.pathnameBase])
        })
      ),
    parentMatches
  );
}

```
在`_renderMatches`中返回由`RouteContext.Provider`包裹的匹配的`element`
通过`reduceRight`将子路由的`element`放到父路由`Provider`的`value`中
```js
function _renderMatches(
  matches: RouteMatch[] | null,
  parentMatches: RouteMatch[] = []
): React.ReactElement | null {
  if (matches == null) return null;

  return matches.reduceRight((outlet, match, index) => {
    return (
      <RouteContext.Provider
        children={
          match.route.element !== undefined ? match.route.element : <Outlet />
        }
        value={{
          outlet,
          matches: parentMatches.concat(matches.slice(0, index + 1))
        }}
      />
    );
  }, null as React.ReactElement | null);
}
```
父路由中的`Outlet`组件通过`useContext`获取子路由的组件进行渲染
```js
export function useOutlet(context?: unknown): React.ReactElement | null {
  let outlet = React.useContext(RouteContext).outlet;
  if (outlet) {
    return (
      <OutletContext.Provider value={context}>{outlet}</OutletContext.Provider>
    );
  }
  return outlet;
}
```