# Frontend State Management Refactor — Design Spec

**Date:** 2026-06-10
**Scope:** Review item #6 — Frontend state management, code organization, and API decoupling
**Approach:** Pilot page (Dashboard) → establish patterns → rollout to other pages

---

## 1. Problem Statement

Current frontend has three issues flagged in architecture review:

1. **React Context for server state**: `useProject`, manual `useEffect` + `useState` fetches in every page. No caching, no background sync, verbose loading/error handling.
2. **API layer coupling**: Pages directly call API functions and manage complex loading states inline.
3. **Code organization**: `components/` depth is shallow; no clear separation between data fetching hooks and UI components.

---

## 2. Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| 1 | Server state managed by TanStack Query | No `useEffect` data fetching in pages; caching works across navigation |
| 2 | Clean hook abstraction | Each domain has a custom hook (`useDashboard`, `useIssues`) wrapping React Query |
| 3 | Reusable loading/error UI | Consistent `<LoadingState>` and `<ErrorState>` components |
| 4 | Pilot validated on Dashboard | Dashboard page fully refactored; patterns documented for rollout |

---

## 3. Architecture

### 3.1 State Ownership Matrix

| State Type | Examples | Solution |
|-----------|----------|----------|
| **Client-only** | auth token, current project, UI theme | Keep in React Context |
| **Server state** | dashboard data, issues list, workflow runs | TanStack Query |
| **Form/local UI** | modal open, form inputs, selected tab | `useState` in component |

### 3.2 New Directory Structure

```
frontend/src/
├── api/                          # Keep existing (axios client + per-entity modules)
├── queries/                      # NEW: TanStack Query configurations
│   ├── queryClient.ts            # QueryClient setup + default options
│   ├── dashboardQueries.ts       # Dashboard query keys + fetch functions
│   ├── issueQueries.ts           # Issue query keys + fetch functions
│   └── workflowQueries.ts        # Workflow query keys + fetch functions
├── hooks/                        # UPDATED
│   ├── useAuth.tsx               # Keep (Context)
│   ├── useProject.tsx            # Keep (Context)
│   ├── useDashboard.ts           # NEW: React Query wrapper
│   ├── useIssues.ts              # NEW: React Query wrapper
│   └── useWorkflows.ts           # NEW: React Query wrapper
├── components/
│   ├── ui/                       # NEW: Reusable UI primitives
│   │   ├── LoadingState.tsx      # Spin with message
│   │   └── ErrorState.tsx        # Error display with retry button
│   └── [existing components...]
└── pages/
    └── Dashboard.tsx             # Pilot: fully refactored
```

### 3.3 QueryClient Configuration

```typescript
// queries/queryClient.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30s before refetch
      gcTime: 5 * 60_000,     // 5min cache retention
      refetchOnWindowFocus: true,
      retry: 2,
    },
  },
});
```

---

## 4. Pilot: Dashboard Refactor

### 4.1 Current State (Problems)

```typescript
// Dashboard.tsx (current)
const [loading, setLoading] = useState(true);
const [data, setData] = useState<DashboardData | null>(null);
const [productivity, setProductivity] = useState<...>(null);
const [planCompletion, setPlanCompletion] = useState<...>(null);

useEffect(() => {
  if (!currentProject) return;
  const fetch = async () => {
    setLoading(true);
    try {
      const [dashboardRes, prodRes, planRes] = await Promise.all([...]);
      setData(dashboardRes.data);
      setProductivity(prodRes);
      setPlanCompletion(planRes);
    } finally {
      setLoading(false);
    }
  };
  fetch();
}, [currentProject, period]);
```

**Issues:**
- 3 separate state variables
- Manual loading/error handling
- No caching → every visit refetches
- No background refresh

### 4.2 Target State

```typescript
// hooks/useDashboard.ts
export function useDashboard(projectId: number | undefined, period: string) {
  return useQuery({
    queryKey: ["dashboard", projectId, period],
    queryFn: async () => {
      const [dashboardRes, prodRes, planRes] = await Promise.all([
        dashboardApi.get({ project_id: projectId }),
        statsApi.agentProductivity(projectId!, period),
        statsApi.planCompletion(projectId!),
      ]);
      return {
        dashboard: dashboardRes.data,
        productivity: prodRes,
        planCompletion: planRes,
      };
    },
    enabled: !!projectId,
  });
}

// pages/Dashboard.tsx
export default function Dashboard() {
  const { currentProject } = useProject();
  const [period, setPeriod] = useState("all");
  const { data, isLoading, error } = useDashboard(currentProject?.id, period);

  if (isLoading) return <LoadingState message="加载 Dashboard..." />;
  if (error) return <ErrorState error={error} onRetry={() => queryClient.invalidateQueries({ queryKey: ["dashboard"] })} />;
  if (!data) return null;

  return <DashboardContent {...data} period={period} onPeriodChange={setPeriod} />;
}
```

**Benefits:**
- Single data object, no manual state juggling
- Cache keyed by `[projectId, period]` → instant switch back
- Background refetch keeps data fresh
- Loading/error handled declaratively

### 4.3 UI Components

```typescript
// components/ui/LoadingState.tsx
export default function LoadingState({ message }: { message?: string }) {
  return (
    <div style={{ textAlign: "center", padding: "100px 0" }}>
      <Spin size="large" />
      {message && <p style={{ marginTop: 16, color: "#888" }}>{message}</p>}
    </div>
  );
}

// components/ui/ErrorState.tsx
export default function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div style={{ textAlign: "center", padding: "100px 0" }}>
      <Alert
        message="加载失败"
        description={error.message}
        type="error"
        showIcon
        action={onRetry ? <Button onClick={onRetry}>重试</Button> : undefined}
      />
    </div>
  );
}
```

---

## 5. Rollout Plan (Post-Pilot)

After Dashboard validates the pattern:

1. **Issues page** (`pages/Issues.tsx`) — most complex: filters, pagination, sorting
2. **Plans page** (`pages/Plans.tsx`) — moderate: list + detail + approval actions
3. **Workflows page** (`pages/Workflows.tsx`) — moderate: new page, good candidate for Query from start
4. **Board page** — DnD complicates things; assess after first 3

Each page gets:
- `queries/{domain}Queries.ts` — query keys + fetch functions
- `hooks/use{Domain}.ts` — React Query wrapper hook
- Refactored page component using new hook + `<LoadingState>` / `<ErrorState>`

---

## 6. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `@tanstack/react-query` | ^5.x | Server state management |
| `@tanstack/react-query-devtools` | ^5.x | DevTools (dev only) |

No other dependencies needed. Works with existing React 19 + TypeScript.

---

## 7. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| TanStack Query v5 breaking changes with React 19 | Low | v5 officially supports React 19; test in pilot |
| Query cache grows unbounded | Low | `gcTime: 5min` limits memory; devtools to monitor |
| Team unfamiliar with Query patterns | Medium | Pilot provides concrete example; document in AGENTS.md |
| Rollout takes too long | Medium | Strict pilot-first: only proceed after Dashboard LGTM |

---

## 8. Testing Strategy

1. **Manual**: Dashboard loads, period switch works, cache hit on navigation back
2. **React Query DevTools**: Verify cache keys, stale time, background refetch
3. **E2E**: Existing Cypress/Playwright tests should pass (no API changes)

---

## 9. Decisions Log

| Decision | Rationale |
|----------|-----------|
| TanStack Query over Zustand/Redux | Query solves the *server state* problem specifically; Zustand/Redux are general-purpose and add boilerplate for caching |
| Keep Context for auth/project | These are client-only state; Context is sufficient and avoids unnecessary dependency |
| Pilot page approach | Validates pattern with low risk before committing to full refactor |
| Dashboard as pilot | Most data-heavy page (3 parallel requests); success here proves the pattern |

---

## 10. Appendix: Query Key Convention

```typescript
// queries/issueQueries.ts
export const issueKeys = {
  all: ["issues"] as const,
  list: (projectId: number, filters: object) => ["issues", "list", projectId, filters] as const,
  detail: (id: number) => ["issues", "detail", id] as const,
};
```

Benefits: centralized keys, easy invalidation (`queryClient.invalidateQueries({ queryKey: issueKeys.all })`).
