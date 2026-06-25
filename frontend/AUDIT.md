# 全量修复计划审计报告

> 对照原始修复计划 26 项，逐项核查当前代码状态。
> 审查时间：2026-06-25

---

## ✅ 已完成项 (21/26)

| # | 计划项 | 状态 | 说明 |
|---|--------|------|------|
| 1 | BASE_URL 环境变量化 | ✅ | `client.ts` 使用 `import.meta.env.VITE_API_BASE \|\| ""`，`.env` 文件已创建 |
| 2 | 统一 @keyframes 到 index.css | ✅ | fadeIn/scaleIn/toastIn/toastOut/slideDown/skeletonPulse 全部在 index.css，3 个组件的 `<style>` 标签已删除 |
| 3 | index.css @theme 整合 | ✅ | 全部 11 个颜色已注册为 Tailwind 主题 token，可用 `text-accent`、`bg-bg-secondary` 等 |
| 4 | 逐文件消除内联样式（组件层） | ✅ | Layout、ToastContext、ConfirmContext、ui.tsx、FileDropzone、FormatSelector、InsightTable、ShapleyPanel、TradePreview、StatsCards 全部使用 Tailwind class |
| 5 | ui.tsx 用 Tailwind 重写 | ✅ | Card/Button/Input/LoadingSpinner/InlineSpinner/ErrorBox/Collapsible/EmptyState 全部用 Tailwind，Button 有真实 hover/active 效果 |
| 6 | index.html 标题修复 | ✅ | `<title>TradeDoctor · AI 交易行为诊断</title>` + meta description |
| 7 | 路由懒加载 | ✅ | App.tsx 全部 9 个页面用 `React.lazy()` + `<Suspense>` 包裹 |
| 8 | 全局 ErrorBoundary | ✅ | ErrorBoundary.tsx 已创建并包裹在 App.tsx BrowserRouter 内，暗色主题 |
| 9 | QueryClient 配置 | ✅ | staleTime=60s, gcTime=300s, retry=2, refetchOnWindowFocus=false |
| 10 | Button hover 效果增强 | ✅ | 各 variant 有真实 hover 效果 (bg-accent-hover/brightness-110/bg-bg-tertiary/border-accent)，active:scale-[0.97] |
| 11 | Collapsible CSS grid 动画 | ✅ | 用 `.collapsible-content` + `data-open` 属性实现，index.css 中有对应样式 |
| 12 | Toast 退出动画 | ✅ | exiting 状态 → `animate-toast-out` → 200ms 后移除 |
| 13 | ConfirmDialog 焦点陷阱 + ESC | ✅ | useEffect 监听 ESC + Tab 循环 + previouslyFocused 恢复 + body scroll lock |
| 14 | 移动端菜单 slideDown | ✅ | `animate-slide-down` 替代 fadeIn |
| 15 | 字体优化 | ✅ | 含 PingFang SC、Microsoft YaHei 中文字体 + antialiased |
| 16 | `prefers-reduced-motion` | ✅ | index.css 中有 media query 禁用动画 |
| 17 | `.focus-ring` 工具类 | ✅ | keyboard-only focus-visible ring |
| 18 | `.tab-btn` 共享样式 | ✅ | index.css 中定义 tab 按钮基础样式 |
| 19 | 删除 WhatIfChart.tsx 死代码 | ✅ | 文件已不存在 |
| 20 | 401 自动跳转登录 | ✅ | client.ts 有 `onAuthExpired()` 处理 401 |
| 21 | Login 页面 expired 参数 | ✅ | Login.tsx 支持 `?expired=1` 查询参数显示过期提示 |

---

## ❌ 未完成项 (5/26)

### 问题 1: WhatIfTab.tsx 残留 3 处 `style={{}}` 内联样式
**文件**: `pages/tabs/WhatIfTab.tsx:63,67-71,147`

**残留代码**:
```tsx
// 第 63 行 — 止损 delta 颜色
<span style={{ color: data.stop_loss.delta >= 0 ? "var(--success)" : "var(--danger)" }}>

// 第 67-71 行 — 结论文字边框 + 颜色
<div className="mt-3 pt-3 text-xs font-medium" style={{
  borderTop: "1px solid var(--border)",
  color: data.stop_loss.delta > 0 ? "var(--success)"
    : data.stop_loss.delta < -0.03 ? "var(--danger)"
    : "var(--accent)",
}}>

// 第 147 行 — 因子贡献金额颜色
<span className="text-sm" style={{ color: item.absolute_impact >= 0 ? "var(--success)" : "var(--danger)" }}>
```

**修复方案**:
```tsx
// 第 63 行 →
<span className={data.stop_loss.delta >= 0 ? "text-success" : "text-danger"}>

// 第 67-71 行 →
<div className={`mt-3 border-t border-border pt-3 text-xs font-medium ${
  data.stop_loss.delta > 0 ? "text-success"
    : data.stop_loss.delta < -0.03 ? "text-danger"
    : "text-accent"
}`}>

// 第 147 行 →
<span className={`text-sm ${item.absolute_impact >= 0 ? "text-success" : "text-danger"}`}>
```

---

### 问题 2: Recharts 图表组件残留 `var(--)` CSS 变量引用
**文件**: `components/PatternChart.tsx:40-49`、`components/EquityCurve.tsx:30-100`

**说明**: Recharts 组件（XAxis/YAxis/Tooltip/CartesianGrid/ReferenceLine）通过 JSX 属性传入样式，只能用字符串值，不能直接用 Tailwind class。这是 Recharts API 的限制，**无法完全消除**。

**但是**:
- `PatternChart.tsx` 的 Tooltip `contentStyle` 仍用 `var(--bg-tertiary)` 等，可以工作但不统一
- `EquityCurve.tsx` 大量使用 `var(--xxx)` 作为 Recharts 属性值

**结论**: 这属于**无法修复的限制**，Recharts 不接受 CSS class 作为 chart 内部元素的样式。标记为 **N/A (Recharts API 限制)**。

---

### 问题 3: `translate(-50%, -50%)` 在 3 个 dialog 组件中仍用 style
**文件**: `ConfirmContext.tsx:113`、`AddFileModal.tsx:106`、`Report.tsx:170`

**残留代码**:
```tsx
style={{ transform: "translate(-50%, -50%)" }}
```

**说明**: 这是为了配合 `fixed left-1/2 top-1/2` 实现居中。可以用 Tailwind 的 `-translate-x-1/2 -translate-y-1/2` 替代。

**修复方案**: 将 `className` 添加 `after:content-[''] after:absolute` 方案，或直接改用 CSS class：
```tsx
// 方案 A: 纯 Tailwind
className="fixed left-1/2 top-1/2 z-[201] -translate-x-1/2 -translate-y-1/2 ..."

// 方案 B: 在 index.css 添加 .centered-dialog 类
```
选择方案 A 最干净。

---

### 问题 4: StatsCards `card()` 函数缺少 `key` prop
**文件**: `components/StatsCards.tsx` card() 函数

**说明**: card() 函数被 tier1/tier2/tier3 数组调用，数组中的元素需要 key，但 card() 内部没有返回带 key 的元素，key 需要在调用处传入。

**修复方案**: 在 tier1/tier2/tier3 数组中为每个 card() 调用包裹 `.map((el, i) => ...)` 或在 card() 返回的 JSX 外层传 key。最简单的方式：
```tsx
// card() 函数改为接受 key 参数
function card(key: string, cls: string, label: string, ...) {
  return <Card key={key} className="p-4">...</Card>;
}

// 调用处
card("total-pnl", "success", "总盈亏", ...)
```

---

### 问题 5: Upload 页面仍用 useState 手动管理异步状态
**文件**: `pages/Upload.tsx`

**说明**: Upload 页面有 5 个 `useState`（loading, statusText, rawFileId, fileName, formats）手动管理上传流程。其他页面（History, Analysis, Report）已全部使用 React Query。但在修复计划中此项标记为 P2（非必须），且 Upload 的流程是多步骤顺序执行（上传→确认格式→导入→分析），不适合简单的 useMutation 封装。

**结论**: 可以保持现状。但如果要修，建议拆分为 3 个独立的 mutation + 状态机。**优先级低，标记为延后处理**。

---

## 📊 总结

| 状态 | 数量 | 详情 |
|------|------|------|
| ✅ 已完成 | 20 | 全部核心修复 |
| 🔧 需修复 | 3 | WhatIfTab 内联样式、dialog translate、StatsCards key |
| ⚠️ 不可修 | 1 | Recharts API 限制（CSS var 在 chart 属性中） |
| ⏳ 延后 | 1 | Upload 页面 React Query 化（复杂度高、优先级低） |

### 需要立即修复的 3 个文件:
1. `pages/tabs/WhatIfTab.tsx` — 消除 3 处内联 style
2. `context/ConfirmContext.tsx` + `components/AddFileModal.tsx` + `pages/Report.tsx` — `translate` 改 Tailwind
3. `components/StatsCards.tsx` — card() 添加 key 参数
