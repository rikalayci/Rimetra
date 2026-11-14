import { api } from "../lib/api";
import { LANGS, useLang, type Lang } from "../lib/i18n";

/** Dil seçici: Türkçe / English. Giriş yapılmışsa tercih sunucuya da kaydedilir (Telegram botu da bu dili kullanır). */
export function LangSwitch({ save = false, className = "" }: { save?: boolean; className?: string }) {
  const { lang, setLang } = useLang();
  const pick = (l: Lang) => {
    if (l === lang) return;
    // Önce kaydet: dil değişince uygulama yeniden kurulup kullanıcıyı sunucudan tekrar okur
    if (save) api("/api/auth/prefs", { method: "PATCH", body: { lang: l } }).catch(() => {}).finally(() => setLang(l));
    else setLang(l);
  };
  return (
    <div className={`grid grid-cols-2 gap-1 ${className}`} role="group" aria-label="Dil / Language">
      {LANGS.map((l) => (
        <button key={l.id} type="button" onClick={() => pick(l.id)}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs ${lang === l.id ? "bg-brandsoft font-bold text-brand" : "hover:bg-surface2"}`}>
          <span aria-hidden>{l.flag}</span>{l.label}
        </button>
      ))}
    </div>
  );
}
