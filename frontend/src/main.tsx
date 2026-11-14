import "@fontsource/nunito-sans/400.css";
import "@fontsource/nunito-sans/600.css";
import "@fontsource/nunito-sans/700.css";
import "@fontsource/nunito-sans/800.css";
import "@fontsource/caveat/500.css";
import "./index.css";

import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/ui";
import { AuthProvider, useAuth } from "./lib/auth";
import { applyTheme } from "./lib/hooks";
import { api } from "./lib/api";
import { getLang, LangProvider, useLang } from "./lib/i18n";
import Admin from "./pages/Admin";
import Calendar from "./pages/Calendar";
import Compare from "./pages/Compare";
import Family from "./pages/Family";
import Login from "./pages/Login";
import ReportPage from "./pages/ReportPage";
import Reports from "./pages/Reports";
import TestDetail from "./pages/TestDetail";
import Unmapped from "./pages/Unmapped";

function App() {
  const { me, loading } = useAuth();
  const { setLang } = useLang();
  // Dil: kullanıcının kayıtlı tercihi uygulanır; tercih yoksa şu anki dil kaydedilir (Telegram botu da onu kullanır).
  useEffect(() => {
    if (!me) return;
    if (me.lang === "tr" || me.lang === "en") {
      if (me.lang !== getLang()) setLang(me.lang);
    } else {
      api("/api/auth/prefs", { method: "PATCH", body: { lang: getLang() } }).catch(() => {});
    }
  }, [me?.id, me?.lang]);
  useEffect(() => {
    if (me?.theme === "light" || me?.theme === "dark" || me?.theme === "system") applyTheme(me.theme);
  }, [me?.theme]);
  if (loading) return <Spinner />;
  if (!me) return <Login />;
  const master = me.role === "master";
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Family />} />
        <Route path="/uye/:memberId" element={<Family />} />
        <Route path="/uye/:memberId/test/:testKey" element={<TestDetail />} />
        <Route path="/rapor/:reportId" element={<ReportPage />} />
        <Route path="/karsilastir" element={<Compare />} />
        <Route path="/tahliller" element={<Reports />} />
        <Route path="/takvim" element={<Calendar />} />
        {master && <Route path="/eslesmemis" element={<Unmapped />} />}
        {master && <Route path="/yonetim" element={<Admin />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <LangProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </LangProvider>
    </BrowserRouter>
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
