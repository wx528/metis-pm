# 019 — useAuth hook 未被使用

> 优先级: P2 | 类型: code-quality | 状态: **fixed**

## 问题描述

`frontend/src/hooks/useAuth.ts` 定义了一个 `useAuth` hook，但整个项目中没有任何地方使用它：

- `App.tsx` 的 `PrivateRoute` 直接读取 `localStorage.getItem("token")`
- `Login.tsx` 直接操作 `localStorage.setItem("token", ...)`
- `client.ts` 的拦截器直接读取 `localStorage.getItem("token")`
- `Layout.tsx` 的登出直接 `localStorage.removeItem("token")`

这导致：
1. **认证状态不响应式**：`PrivateRoute` 只在组件挂载时检查 token，登录后不会自动更新
2. **代码重复**：token 的读写散落在多个文件中
3. **死代码**：`useAuth` 是无用代码

## 涉及文件

- `frontend/src/hooks/useAuth.ts` — 未被使用
- `frontend/src/App.tsx` L16-L18 — 直接读 localStorage
- `frontend/src/pages/Login.tsx` L22 — 直接写 localStorage
- `frontend/src/components/Layout.tsx` L34 — 直接删 localStorage

## 修复方案

方案 A：使用 `useAuth` hook 统一管理认证状态

将 token 状态提升到 Context，让 `PrivateRoute`、`Login`、`Layout` 都通过 `useAuth` 操作：

```tsx
// AuthProvider 包裹 App
// PrivateRoute 使用 useAuth().isLoggedIn
// Login 使用 useAuth().login(token)
// Layout 使用 useAuth().logout()
```

方案 B：删除 `useAuth` hook，保持当前简单实现

如果项目不需要响应式认证状态，可以删除 `useAuth.ts` 避免混淆。
