# 前端 SSE 解析不健壮

## 优先级: P2
## 状态: open
## 类型: bug

## 问题描述

`useNotifications.tsx` 中 SSE 流解析按 `\n` 分割并匹配 `data: ` 前缀。但 SSE 规范中一个 event 可能跨多个 chunk，`data:` 行可能被截断。当前实现可能丢失或错误解析跨 chunk 的消息。

## 影响范围

- 网络较慢或消息较大时可能出现通知解析失败
- 实际使用中因为通知 JSON 通常较小，问题不常见

## 建议方案

1. 实现更健壮的 SSE 解析器：维护 buffer，按 `\n\n` 分割完整 event
2. 或使用第三方库如 `eventsource-parser`
3. 或等待浏览器 `EventSource` 支持自定义 header 后切换回标准 API

## 参考

SSE 规范：https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream
