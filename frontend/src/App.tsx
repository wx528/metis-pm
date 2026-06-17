import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Issues from "./pages/Issues";
import IssueDetail from "./pages/IssueDetail";
import Plans from "./pages/Plans";
import PlanDetail from "./pages/PlanDetail";

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/projects/default/dashboard" replace />} />
            <Route path="issues/:id" element={<IssueDetail />} />
            <Route path="plans/:id" element={<PlanDetail />} />
            <Route path="projects/:projectSlug/dashboard" element={<Dashboard />} />
            <Route path="projects/:projectSlug/issues" element={<Issues />} />
            <Route path="projects/:projectSlug/issues/:id" element={<IssueDetail />} />
            <Route path="projects/:projectSlug/plans" element={<Plans />} />
            <Route path="projects/:projectSlug/plans/:id" element={<PlanDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
