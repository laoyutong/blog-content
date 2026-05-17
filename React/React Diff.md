## 原则
- 只对同级元素进行Diff
- 两个不同类型的元素会产生出不同的树
- 开发者可以通过 key prop来暗示哪些子元素在不同的渲染下能保持稳定

## 单节点
```js
function reconcileSingleElement(
  returnFiber: Fiber,
  currentFirstChild: Fiber | null,
  element: ReactElement
): Fiber {
  const key = element.key;
  let child = currentFirstChild;
  
  // 首先判断是否存在对应DOM节点
  while (child !== null) {
    // 上一次更新存在DOM节点，接下来判断是否可复用
    // 首先比较key是否相同
    if (child.key === key) {
      // key相同，接下来比较type是否相同
      switch (child.tag) {
        // ...省略case
        
        default: {
          if (child.elementType === element.type) {
            // type相同则表示可以复用
            // 返回复用的fiber
            return existing;
          }
          
          // type不同则跳出switch
          break;
        }
      }
      // 代码执行到这里代表：key相同但是type不同
      // 将该fiber及其兄弟fiber标记为删除
      deleteRemainingChildren(returnFiber, child);
      break;
    } else {
      // key不同，将该fiber标记为删除
      deleteChild(returnFiber, child);
    }
    child = child.sibling;
  }
  // 创建新Fiber，并返回
}
```
> 以  ul > li * 3（当前页面显示的） => ul > p（这次需要更新的)  为🌰

当**key**相同且**type**不同时，代表我们已经找到本次更新的p对应的上次的fiber，但是p与li type不同，不能复用。既然唯一的可能性已经不能复用，则剩下的fiber都没有机会了，所以都需要标记删除。
当**key**不同时只代表遍历到的该fiber不能被p复用，所以仅仅标记该fiber删除，继续遍历兄弟fiber

## 多节点
> 相较于新增和删除，更新组件发生的频率更高。所以Diff会优先判断当前节点是否属于更新

### 第一轮遍历
1. let i = 0，遍历newChildren，将newChildren[i]与oldFiber比较，判断DOM节点是否可复用。
2. 如果可复用，i++，继续比较newChildren[i]与oldFiber.sibling，可以复用则继续遍历。
3. 如果key不同则跳出循环；如果type不同则创建一个新的继续遍历，并删除没有复用的老节点

### 第二轮遍历
newChildren没遍历完，oldFiber遍历完
需要遍历剩下的newChildren为生成的workInProgress fiber依次标记Placement。

newChildren遍历完，oldFiber没遍历完
遍历剩下的oldFiber，依次标记Deletion。

newChildren与oldFiber都没遍历完
则处理移动的节点

## 移动节点处理
将所有还未处理的oldFiber存入以key为key，oldFiber为value的Map中。
遍历剩余的newChildren，通过newChildren[i].key就能在existingChildren中找到key相同的oldFiber
```js
function mapRemainingChildren(
    returnFiber: Fiber,
    currentFirstChild: Fiber,
  ): Map<string | number, Fiber> {
    // Add the remaining children to a temporary map so that we can find them by
    // keys quickly. Implicit (null) keys get added to this set with their index
    // instead.
    const existingChildren: Map<string | number, Fiber> = new Map();

    let existingChild = currentFirstChild;
    while (existingChild !== null) {
      if (existingChild.key !== null) {
        existingChildren.set(existingChild.key, existingChild);
      } else {
        existingChildren.set(existingChild.index, existingChild);
      }
      existingChild = existingChild.sibling;
    }
    return existingChildren;
  }

```
## 标记节点移动
节点是否移动以最后一个可复用的节点在oldFiber中的位置索引（用变量lastPlacedIndex表示）为参照物
比较遍历到的可复用节点在上次更新时是否也在lastPlacedIndex对应的oldFiber后面，就能知道两次更新中这两个节点的相对位置改变没有。
用变量oldIndex表示遍历到的可复用节点在oldFiber中的位置索引。如果oldIndex < lastPlacedIndex，代表本次更新该节点需要向右移动。
lastPlacedIndex初始为0，每遍历一个可复用的节点，如果oldIndex >= lastPlacedIndex，则lastPlacedIndex = oldIndex。

🌰：
```js
// 之前
abcd
// 之后
dabc
```
> 当前oldFiber：abcd、当前newChildren dabc

key === d 在 oldFiber中存在，此时 oldIndex === 3
比较 oldIndex 与 lastPlacedIndex，oldIndex 3 > lastPlacedIndex 0，则 lastPlacedIndex = 3
d节点位置不变

> 当前oldFiber：abc、当前newChildren abc

key === a 在 oldFiber中存在，此时 oldIndex === 0
比较 oldIndex 与 lastPlacedIndex;，oldIndex 0 < lastPlacedIndex 3
**则 a节点需要向右移动**