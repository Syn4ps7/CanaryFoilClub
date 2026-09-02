import { useState } from "react";
import { motion } from "framer-motion";
import { Lock, ArrowRight } from "lucide-react";
import { adminApi, setToken, formatApiError } from "@/lib/adminApi";

const inputCls =
  "w-full rounded-xl border border-white/15 bg-deep px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-glow/70";

const AdminLogin = ({ onSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await adminApi.post("/auth/login", { email, password });
      setToken(data.token);
      onSuccess({ email: data.email, role: data.role });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-abyss noise-overlay flex items-center justify-center px-6 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-glow/10 blur-[140px]" />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md rounded-3xl border border-white/10 bg-panel/80 backdrop-blur-xl p-8 sm:p-10"
        data-testid="admin-login-card"
      >
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90">Espace privé</p>
        <h1 className="mt-3 font-syne text-3xl font-extrabold tracking-tight">
          Canary <span className="text-glow">Foil</span> Club
        </h1>
        <p className="mt-2 text-sm text-slate-400">Tableau de bord propriétaire — connexion requise.</p>

        <form onSubmit={submit} className="mt-8 space-y-5">
          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">Email</label>
            <input
              data-testid="admin-login-email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputCls}
              placeholder="admin@canaryfoilclub.com"
            />
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">Mot de passe</label>
            <input
              data-testid="admin-login-password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputCls}
              placeholder="••••••••••"
            />
          </div>
          {error && (
            <p data-testid="admin-login-error" className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </p>
          )}
          <motion.button
            data-testid="admin-login-submit"
            type="submit"
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.02 }}
            whileTap={{ scale: loading ? 1 : 0.97 }}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-glow py-4 font-syne text-sm font-bold text-abyss btn-glow disabled:opacity-60"
          >
            <Lock size={15} />
            {loading ? "Connexion…" : "Se connecter"}
            <ArrowRight size={15} />
          </motion.button>
        </form>
        <a href="/" className="mt-6 inline-block text-xs text-slate-500 transition-colors hover:text-glow" data-testid="admin-back-to-site">
          ← Retour au site
        </a>
      </motion.div>
    </div>
  );
};

export default AdminLogin;
