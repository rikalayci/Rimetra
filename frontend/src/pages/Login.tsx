import { Loader2 } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { api, type Me } from "../lib/api";
import { useAuth } from "../lib/auth";
import { applyTheme } from "../lib/hooks";
import { HomeIllustration, Logo } from "../components/icons";
import { LangSwitch } from "../components/LangSwitch";
import { ErrorBox } from "../components/ui";

export default function Login() {
  const { setMe } = useAuth();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const me = await api<Me>("/api/auth/login", { body: { username, password } });
      if (me.theme === "light" || me.theme === "dark" || me.theme === "system") applyTheme(me.theme);
      setMe(me);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-2 h-36"><HomeIllustration /></div>
        <form onSubmit={submit} className="card space-y-5 p-7">
          <div className="flex items-center gap-2">
            <Logo size={40} />
            <div>
              <div className="text-3xl font-extrabold tracking-tight text-brand">{t("Rimetra")}</div>
              <div className="text-sm text-muted">{t("Aile tahlil takibi")}</div>
            </div>
          </div>
          <div className="space-y-3">
            <label className="block">
              <span className="label">{t("Kullanıcı adı")}</span>
              <input className="input py-2.5" autoComplete="username" autoFocus value={username} onChange={(e) => setU(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">{t("Şifre")}</span>
              <input className="input py-2.5" type="password" autoComplete="current-password" value={password} onChange={(e) => setP(e.target.value)} />
            </label>
          </div>
          <ErrorBox error={err} />
          <button className="btn-primary w-full py-2.5" disabled={busy || !username || !password}>
            {busy && <Loader2 size={16} className="animate-spin" />} {" "}{t("Giriş yap")}</button>
        </form>
        <LangSwitch className="mx-auto mt-4 max-w-[220px]" />
        <p className="mt-6 text-center font-hand text-2xl text-[#B9826A]">{t("Daha sağlıklı, daha mutlu yarınlara birlikte ♡")}</p>
      </div>
    </div>
  );
}
