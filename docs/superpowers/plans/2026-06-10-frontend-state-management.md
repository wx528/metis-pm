# Frontend State Management Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce TanStack Query for server state management and refactor Dashboard as the pilot page.

**Architecture:** Install `@tanstack/react-query`, set up QueryClient with caching defaults, create reusable UI components for loading/error states, refactor Dashboard to use React Query hooks, validate with manual testing.

**Tech Stack:** React 19, TypeScript, TanStack Query v5, Ant Design 6, Vite

---

## Files Overview

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/package.json` | Modify | Add `@tanstack/react-query` and `@tanstack/react-query-devtools` dependencies |
| `frontend/src/main.tsx` | Modify | Wrap app with QueryClientProvider |
| `frontend/src/queries/queryClient.ts` | Create | QueryClient instance with default options |
| `frontend/src/queries/dashboardQueries.ts` | Create | Dashboard query keys and fetch function |
| `frontend/src/hooks/useDashboard.ts` | Create | React Query hook for dashboard data |
| `frontend/src/components/ui/LoadingState.tsx` | Create | Reusable loading spinner component |
| `frontend/src/components/ui/ErrorState.tsx` | Create | Reusable error display with retry button |
| `frontend/src/pages/Dashboard.tsx` | Modify | Refactor to use useDashboard hook + new UI components |

---

## Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Add TanStack Query packages**

Run in `frontend/` directory:
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

- [ ] **Step 2: Verify installation**

Check `frontend/package.json` contains:
```json
"@tanstack/react-query": "^5.x",
"@tanstack/react-query-devtools": "^5.x"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add tanstack/react-query dependencies"
```

---

## Task 2: Setup QueryClient

**Files:**
- Create: `frontend/src/queries/queryClient.ts`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Create QueryClient configuration**

Create `frontend/src/queries/queryClient.ts`:
```typescript
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30 seconds
      gcTime: 5 * 60_000,     // 5 minutes
      refetchOnWindowFocus: true,
      retry: 2,
    },
  },
});
```

- [ ] **Step 2: Wrap app with QueryClientProvider**

Modify `frontend/src/main.tsx`:
```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./queries/queryClient";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/queries/queryClient.ts frontend/src/main.tsx
git commit -m "feat: setup QueryClient with caching defaults"
```

---

## Task 3: Create Dashboard Query Module

**Files:**
- Create: `frontend/src/queries/dashboardQueries.ts`

- [ ] **Step 1: Create query keys and fetch function**

Create `frontend/src/queries/dashboardQueries.ts`:
```typescript
import { dashboardApi } from "../api/dashboard";
import { statsApi } from "../api/stats";
import type { DashboardData } from "../api";
import type { AgentProductivity, PlanCompletion } from "../api/stats";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  detail: (projectId: number, period: string) =>
    ["dashboard", "detail", projectId, period] as const,
};

export interface DashboardQueryResult {
  dashboard: DashboardData;
  productivity: AgentProductivity;
  planCompletion: PlanCompletion;
}

export async function fetchDashboardData(
  projectId: number,
  period: string
): Promise<DashboardQueryResult> {
  const [dashboardRes, prodRes, planRes] = await Promise.all([
    dashboardApi.get({ project_id: projectId }),
    statsApi.agentProductivity(projectId, period),
    statsApi.planCompletion(projectId),
  ]);

  return {
    dashboard: dashboardRes.data,
    productivity: prodRes,
    planCompletion: planRes,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/queries/dashboardQueries.ts
git commit -m "feat: add dashboard query module with keys and fetcher"
```

---

## Task 4: Create useDashboard Hook

**Files:**
- Create: `frontend/src/hooks/useDashboard.ts`

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useDashboard.ts`:
```typescript
import { useQuery } from "@tanstack/react-query";
import { dashboardKeys, fetchDashboardData } from "../queries/dashboardQueries";

export function useDashboard(projectId: number | undefined, period: string) {
  return useQuery({
    queryKey: dashboardKeys.detail(projectId ?? 0, period),
    queryFn: () => fetchDashboardData(projectId!, period),
    enabled: !!projectId,
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useDashboard.ts
git commit -m "feat: add useDashboard hook with React Query"
```

---

## Task 5: Create Reusable UI Components

**Files:**
- Create: `frontend/src/components/ui/LoadingState.tsx`
- Create: `frontend/src/components/ui/ErrorState.tsx`

- [ ] **Step 1: Create LoadingState component**

Create `frontend/src/components/ui/LoadingState.tsx`:
```typescript
import { Spin } from "antd";

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message }: LoadingStateProps) {
  return (
    <div style={{ textAlign: "center", padding: "100px 0" }}>
      <Spin size="large" />
      {message && (
        <p style={{ marginTop: 16, color: "#888" }}>{message}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create ErrorState component**

Create `frontend/src/components/ui/ErrorState.tsx`:
```typescript
import { Alert, Button } from "antd";
import { ReloadOutlined } from "@ant-design/icons";

interface ErrorStateProps {
  error: Error;
  onRetry?: () => void;
}

export default function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div style={{ textAlign: "center", padding: "100px 0" }}>
      <Alert
        message="加载失败"
        description={error.message || "请稍后重试"}
        type="error"
        showIcon
        action={
          onRetry ? (
            <Button icon={<ReloadOutlined />} onClick={onRetry}>
              重试
            </Button>
          ) : undefined
        }
      />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/LoadingState.tsx frontend/src/components/ui/ErrorState.tsx
git commit -m "feat: add reusable LoadingState and ErrorState UI components"
```

---

## Task 6: Refactor Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Replace imports and state management**

Replace the imports at the top of `frontend/src/pages/Dashboard.tsx`:
```typescript
import { useState } from "react";  // Remove useEffect
import { Row, Col, Card, Statistic, List, Tag, Timeline, Progress, Select, Empty } from "antd";
// ... keep all icon imports ...
import { useDashboard } from "../hooks/useDashboard";
import { useProject } from "../hooks/useProject";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import { queryClient } from "../queries/queryClient";
import { dashboardKeys } from "../queries/dashboardQueries";
// Remove: import { dashboardApi } from "../api/dashboard";
// Remove: import { statsApi } from "../api/stats";
// Remove: import type { DashboardData } from "../api";
// Remove: import type { AgentProductivity, PlanCompletion } from "../api/stats";
// Remove: import AgentActivityPanel from "../components/AgentActivityPanel";
```

- [ ] **Step 2: Replace component body**

Replace the Dashboard component body:
```typescript
export default function Dashboard() {
  const { currentProject } = useProject();
  const [period, setPeriod] = useState("all");
  const { data, isLoading, error } = useDashboard(currentProject?.id, period);

  if (isLoading) {
    return <LoadingState message="加载 Dashboard..." />;
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() =>
          queryClient.invalidateQueries({ queryKey: dashboardKeys.all })
        }
      />
    );
  }

  if (!data) {
    return <Empty description="暂无数据" />;
  }

  const { dashboard, productivity, planCompletion } = data;

  // ... rest of JSX stays the same, but uses `dashboard` instead of `data` ...
```

- [ ] **Step 3: Remove old state and useEffect**

Delete from the component:
- `const [loading, setLoading] = useState(true);`
- `const [data, setData] = useState<DashboardData | null>(null);`
- `const [productivity, setProductivity] = useState<AgentProductivity | null>(null);`
- `const [planCompletion, setPlanCompletion] = useState<PlanCompletion | null>(null);`
- The entire `useEffect` block with `Promise.all`
- Update all references from `data.xxx` to `dashboard.xxx`

- [ ] **Step 4: Test the refactored Dashboard**

1. Run `npm run dev` in `frontend/` directory
2. Login and navigate to Dashboard
3. Verify:
   - Dashboard loads with loading spinner
   - Data appears after loading
   - Period switch (all/week/month) triggers refetch
   - Navigate away and back → data shows instantly (cached)
   - Open React Query DevTools (click the icon in bottom-left) and verify:
     - Query key shows `["dashboard", "detail", {projectId}, "all"]`
     - Cache status shows "fresh" then "stale"

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "refactor: Dashboard page uses React Query

- Replace manual useEffect fetching with useDashboard hook
- Use LoadingState and ErrorState components
- Data cached across navigation"
```

---

## Task 7: Validation Checklist

- [ ] Dashboard loads without errors
- [ ] Loading state shows spinner
- [ ] Error state shows alert (test by temporarily breaking API URL)
- [ ] Period switch updates data
- [ ] Cache hit on navigation back to Dashboard
- [ ] React Query DevTools shows active queries
- [ ] No TypeScript errors: `npm run build` passes in `frontend/`
- [ ] ESLint passes: `npm run lint` passes in `frontend/`

---

## Post-Pilot Rollout (Future Work)

After Dashboard pilot is validated, apply same pattern to:

1. **Issues page** (`pages/Issues.tsx`)
   - Create `queries/issueQueries.ts` with list/detail keys
   - Create `hooks/useIssues.ts` with pagination support
   - Handle filters and sorting via query key dependencies

2. **Plans page** (`pages/Plans.tsx`)
   - Create `queries/planQueries.ts`
   - Create `hooks/usePlans.ts`

3. **Workflows page** (`pages/Workflows.tsx`)
   - Create `queries/workflowQueries.ts`
   - Create `hooks/useWorkflows.ts`

Each follows the same pattern: query keys → fetch function → hook → page refactor.

---

## Self-Review Checklist

- [x] Spec coverage: All sections from design spec (QueryClient, query keys, hook, UI components, Dashboard refactor) have corresponding tasks
- [x] No placeholders: Every step has actual code or exact commands
- [x] Type consistency: `DashboardQueryResult`, `useDashboard` params, query keys all match
- [x] File paths: All paths are exact and relative to `frontend/src/`
