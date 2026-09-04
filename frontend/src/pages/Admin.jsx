import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { adminApi, clearToken, getToken } from "@/lib/adminApi";
import AdminLogin from "@/components/admin/AdminLogin";
import AdminLayout from "@/components/admin/AdminLayout";
import AdminDashboard from "@/components/admin/AdminDashboard";
import AdminBookings from "@/components/admin/AdminBookings";
import AdminPlanning from "@/components/admin/AdminPlanning";
import AdminReviews from "@/components/admin/AdminReviews";

export default function Admin() {
  const [auth, setAuth] = useState(null);

  useEffect(() => {
    document.title = "Admin — Canary Foil Club";
    if (!getToken()) {
      setAuth(false);
      return;
    }
    adminApi
      .get("/auth/me")
      .then(({ data }) => setAuth(data))
      .catch(() => {
        clearToken();
        setAuth(false);
      });
  }, []);

  const logout = () => {
    clearToken();
    setAuth(false);
  };

  if (auth === null) {
    return (
      <div className="min-h-screen bg-abyss grid place-items-center">
        <div className="h-8 w-8 rounded-full border-2 border-glow/30 border-t-glow animate-spin" data-testid="admin-loading" />
      </div>
    );
  }

  if (!auth) return <AdminLogin onSuccess={setAuth} />;
  return (
    <AdminLayout admin={auth} onLogout={logout}>
      <Routes>
        <Route index element={<AdminDashboard onLogout={logout} />} />
        <Route path="bookings" element={<AdminBookings onLogout={logout} />} />
        <Route path="planning" element={<AdminPlanning onLogout={logout} />} />
        <Route path="reviews" element={<AdminReviews onLogout={logout} />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </AdminLayout>
  );
}
