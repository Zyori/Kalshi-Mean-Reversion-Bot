import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { MarketsPage } from "./pages/MarketsPage";
import { TradesPage } from "./pages/TradesPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { DataPage } from "./pages/DataPage";
import { LoginPage } from "./pages/LoginPage";
import { PublicStatusPage } from "./pages/PublicStatusPage";
import { useAuth } from "./hooks/useAuth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function isPublicHost(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  if (params.get("view") === "public") return true;
  if (params.get("view") === "admin") return false;
  // Single-domain for now: admin lives at lutz.bot; public summary ships
  // when mrb.lutz.bot is split off (then flip this to the mrb.* check).
  return false;
}

function ProtectedRoutes() {
  const { authed, isLoading } = useAuth();
  if (isLoading) return null;
  if (!authed) return <Navigate to="/login" replace />;
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<MarketsPage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="trades" element={<TradesPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function AdminApp() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  );
}

function PublicApp() {
  return (
    <Routes>
      <Route path="/" element={<PublicStatusPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const publicMode = isPublicHost();
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{publicMode ? <PublicApp /> : <AdminApp />}</BrowserRouter>
    </QueryClientProvider>
  );
}
