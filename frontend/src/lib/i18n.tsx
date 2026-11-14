import { createContext, Fragment, useCallback, useContext, useState, type ReactNode } from "react";
import { EN } from "../locales/en";

/**
 * Dil desteği. Kaynak metinler Türkçedir ve aynı zamanda çeviri anahtarıdır:
 *   t("Raporlar")            → "Reports" (İngilizcede)
 *   t("{n} ölçüm", { n: 3 }) → "3 measurements"
 * Dil değişince uygulama yeniden çizilir (LangProvider).
 */
export type Lang = "tr" | "en";
export const LANGS: { id: Lang; label: string; flag: string }[] = [
  { id: "tr", label: "Türkçe", flag: "🇹🇷" },
  { id: "en", label: "English", flag: "🇬🇧" },
];

const KEY = "rimetra-lang";

function detect(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "tr" || saved === "en") return saved;
  } catch {}
  const nav = (navigator.languages?.[0] || navigator.language || "tr").toLowerCase();
  return nav.startsWith("tr") ? "tr" : nav.startsWith("en") ? "en" : "tr";
}

let current: Lang = detect();
document.documentElement.lang = current;

export const getLang = () => current;
/** Intl biçimlendirme için yerel ayar. */
export const locale = () => (current === "en" ? "en-GB" : "tr-TR");

export function t(s: string, vars?: Record<string, string | number | null | undefined>): string {
  let out = current === "en" ? (EN[s] ?? s) : s;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k] ?? "") : m));
  return out;
}

/** Kaydedilmiş dili uygular (sunucudaki kullanıcı tercihi gibi). Değiştiyse true döner. */
export function applyLang(l: string | null | undefined): boolean {
  if ((l !== "tr" && l !== "en") || l === current) return false;
  current = l;
  document.documentElement.lang = l;
  try {
    localStorage.setItem(KEY, l);
  } catch {}
  return true;
}

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: current, setLang: () => {} });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setState] = useState<Lang>(current);
  const setLang = useCallback((l: Lang) => {
    applyLang(l);
    setState(l);
  }, []);
  // key: dil değişince tüm ağaç yeni metinlerle yeniden kurulur
  return (
    <Ctx.Provider value={{ lang, setLang }}>
      <Fragment key={lang}>{children}</Fragment>
    </Ctx.Provider>
  );
}

export const useLang = () => useContext(Ctx);
