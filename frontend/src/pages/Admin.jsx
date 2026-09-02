import { useEffect, useState } from "react";
import { adminApi, clearToken, getToken } from "@/lib/adminApi";
import AdminLogin from "@/components/admin/AdminLogin";
import AdminDashboard from "@/components/admin/AdminDashboard";

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
  return <AdminDashboard admin={auth} onLogout={logout} />;
}
