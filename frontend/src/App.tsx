import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { ProjectProvider } from "./hooks/useProject";
import { NotificationProvider } from "./hooks/useNotifications";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Board from "./pages/Board";
import Workflows from "./pages/Workflows";
import Issues from "./pages/Issues";
import IssueDetail from "./pages/IssueDetail";
import Milestones from "./pages/Milestones";
import Plans from "./pages/Plans";
import PlanDetail from "./pages/PlanDetail";
import Servers from "./pages/Servers";
import Projects from "./pages/Projects";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <ProjectProvider>
                    <NotificationProvider>
                      <Layout />
                    </NotificationProvider>
                  </ProjectProvider>
                </PrivateRoute>
              }
            >
              {/* 兼容旧路由 → 重定向到 default 项目 */}
              <Route index element={<Navigate to="/projects/default/dashboard" replace />} />
              <Route path="issues" element={<Navigate to="/projects/default/issues" replace />} />
              <Route path="issues/:id" element={<IssueDetail />} />
              <Route path="milestones" element={<Navigate to="/projects/default/milestones" replace />} />
              <Route path="plans" element={<Navigate to="/projects/default/plans" replace />} />
              <Route path="plans/:id" element={<PlanDetail />} />
              <Route path="servers" element={<Navigate to="/projects/default/servers" replace />} />

              {/* 项目管理（跨项目，不绑定 slug） */}
              <Route path="projects" element={<Projects />} />

              {/* 新路由：带项目 slug */}
              <Route path="projects/:projectSlug/dashboard" element={<Dashboard />} />
              <Route path="projects/:projectSlug/board" element={<Board />} />
              <Route path="projects/:projectSlug/issues" element={<Issues />} />
              <Route path="projects/:projectSlug/issues/:id" element={<IssueDetail />} />
              <Route path="projects/:projectSlug/milestones" element={<Milestones />} />
              <Route path="projects/:projectSlug/plans" element={<Plans />} />
              <Route path="projects/:projectSlug/plans/:id" element={<PlanDetail />} />
              <Route path="projects/:projectSlug/servers" element={<Servers />} />
              <Route path="projects/:projectSlug/workflows" element={<Workflows />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
}

export default App;
