import type { Flag, ResultRow } from "./api";
import { getLang, locale, t } from "./i18n";

export const fmtDate = (s?: string | null) => {
  if (!s) return "—";
  const d = new Date(s.length === 10 ? s + "T00:00:00" : s);
  return d.toLocaleDateString(locale(), { day: "2-digit", month: getLang() === "en" ? "short" : "2-digit", year: "numeric" });
};

export const fmtDateTime = (s?: string | null) => {
  if (!s) return "—";
  const d = new Date(s);
  return d.toLocaleString(locale(), {
    day: "2-digit", month: getLang() === "en" ? "short" : "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
};

export const fmtMonth = (s: string) => new Date(s).toLocaleDateString(locale(), { month: "short", year: "numeric" });

export const fmtNum = (n: number | null | undefined, digits = 3) => {
  if (n === null || n === undefined || Number.isNaN(n)) return "";
  const abs = Math.abs(n);
  const maxFrac = abs >= 100 ? 1 : abs >= 10 ? 2 : digits;
  return n.toLocaleString(locale(), { maximumFractionDigits: maxFrac });
};

export const valueText = (r: Pick<ResultRow, "value_numeric" | "value_text" | "value_qualifier" | "raw_value">) => {
  const parts: string[] = [];
  if (r.value_text) parts.push(r.value_text);
  if (r.value_numeric !== null && r.value_numeric !== undefined)
    parts.push(`${r.value_qualifier ?? ""}${fmtNum(r.value_numeric)}`);
  return parts.join(" ") || r.raw_value || "—";
};

export const refText = (r: Pick<ResultRow, "ref_low" | "ref_high" | "ref_text" | "ref_low_exclusive" | "ref_high_exclusive">) => {
  if (r.ref_low !== null && r.ref_high !== null) return `${fmtNum(r.ref_low)}–${fmtNum(r.ref_high)}`;
  if (r.ref_high !== null) return `${r.ref_high_exclusive ? "<" : "≤"}${fmtNum(r.ref_high)}`;
  if (r.ref_low !== null) return `${r.ref_low_exclusive ? ">" : "≥"}${fmtNum(r.ref_low)}`;
  if (r.ref_text) return r.ref_text;
  return "—";
};

// Getter'lar: o anki dilde okunur (FLAG_LABEL[flag] kullanımı değişmez)
export const FLAG_LABEL: Record<Flag, string> = {
  get normal() { return t("Normal"); },
  get high() { return t("Yüksek"); },
  get low() { return t("Düşük"); },
  get abnormal() { return t("Anormal"); },
  get unknown() { return t("Belirsiz"); },
};

export const isOut = (f: Flag) => f === "high" || f === "low" || f === "abnormal";

export const SPECIMEN_LABEL: Record<string, string> = {
  get blood() { return t("Kan"); },
  get serum() { return t("Serum"); },
  get plasma() { return t("Plazma"); },
  get urine() { return t("İdrar"); },
  get other() { return t("Diğer"); },
};

/** Kategori adı (veride Türkçe anahtar olarak durur; ekranda çevrilir). */
export const catLabel = (c: string | null | undefined) => (c ? t(c) : "");

/** Birim (ör. "sn" → "s"). */
export const unitLabel = (u: string | null | undefined) => (u ? t(u) : u ?? "");

export const AVATAR_COLORS = ["#F6D5C3", "#F3E1C7", "#DDE9DA", "#F7D9D9", "#DCE4F0", "#EADCF0", "#F2E6B8"];

export const colorFor = (id: string, explicit?: string | null) => {
  if (explicit) return explicit;
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
};

export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toLocaleUpperCase("tr-TR"))
    .join("");

export const possessive = (name: string) => {
  if (getLang() === "en") return name.endsWith("s") ? `${name}'` : `${name}'s`;
  // Türkçe iyelik eki: Burak'ın, Ayşe'nin, Mehmet'in, Zeynep'in
  const vowels = "aeıioöuü";
  const lower = name.toLocaleLowerCase("tr-TR");
  const lastVowel = [...lower].reverse().find((c) => vowels.includes(c)) ?? "e";
  const endsVowel = vowels.includes(lower[lower.length - 1] ?? "");
  const map: Record<string, string> = { a: "ın", ı: "ın", e: "in", i: "in", o: "un", u: "un", ö: "ün", ü: "ün" };
  const suf = map[lastVowel] ?? "in";
  return `${name}'${endsVowel ? "n" : ""}${suf}`;
};

export const todayISO = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
