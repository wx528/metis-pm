import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Issues from "./pages/Issues";
import IssueDetail from "./pages/IssueDetail";
import Milestones from "./pages/Milestones";
import Plans from "./pages/Plans";
import PlanDetail from "./pages/PlanDetail";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token");
  return token ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="issues" element={<Issues />} />
            <Route path="issues/:id" element={<IssueDetail />} />
            <Route path="milestones" element={<Milestones />} />
            <Route path="plans" element={<Plans />} />
            <Route path="plans/:id" element={<PlanDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
