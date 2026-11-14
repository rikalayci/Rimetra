import { BarChart3, CalendarDays, Home, KeyRound, LogOut, Monitor, Moon, Search, Send, Settings, Sun, Unlink } from "lucide-react";
import { t } from "../lib/i18n";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate } from "../lib/format";
import { applyTheme, currentTheme, type Theme } from "../lib/hooks";
import { Avatar } from "./Avatar";
import { Logo } from "./icons";
import { TelegramModal } from "./TelegramConnect";
import { LangSwitch } from "./LangSwitch";
import { ErrorBox, Field, Modal } from "./ui";

function NavItem({ to, icon, children, end }: { to: string; icon: ReactNode; children: ReactNode; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `relative flex items-center gap-2 whitespace-nowrap px-1 py-2 text-[15px] font-semibold transition ${
          isActive ? "text-brand after:absolute after:inset-x-0 after:-bottom-[13px] after:h-[3px] after:rounded-full after:bg-brand" : "text-muted hover:text-ink"
        }`
      }
    >
      {icon}
      {children}
    </NavLink>
  );
}

function SearchBox() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setRes(null);
      return;
    }
    const ctl = new AbortController();
    const tx = setTimeout(() => {
      api(`/api/app/search?q=${encodeURIComponent(q.trim())}`, { signal: ctl.signal }).then(setRes).catch(() => {});
    }, 200);
    return () => {
      clearTimeout(tx);
      ctl.abort();
    };
  }, [q]);

  useEffect(() => {
    const h = (e: MouseEvent) => box.current && !box.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const go = (to: string) => {
    setOpen(false);
    setQ("");
    nav(to);
  };
  const empty = res && !res.tests.length && !res.reports.length && !res.notes.length;

  return (
    <div ref={box} className="relative w-full max-w-sm">
      <Search size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={t("Kayıt, tahlil veya not ara...")}
        className="w-full rounded-2xl border border-line bg-surface py-2.5 pl-10 pr-3 text-sm outline-none placeholder:text-muted focus:border-brand"
      />
      {open && res && (
        <div className="card absolute right-0 top-12 z-40 max-h-[70vh] w-full min-w-[320px] overflow-y-auto p-2">
          {empty && <div className="px-3 py-4 text-sm text-muted">{t("Sonuç bulunamadı.")}</div>}
          {res.tests.length > 0 && <div className="px-3 pb-1 pt-2 text-xs font-bold uppercase text-muted">{t("Testler")}</div>}
          {res.tests.map((tx: any) => (
            <button key={tx.member_id + tx.test_key} onClick={() => go(`/uye/${tx.member_id}/test/${tx.test_key}`)}
              className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-surface2">
              <span className="font-semibold">{tx.display_name}</span>
              <span className="text-muted">{tx.member_name}</span>
            </button>
          ))}
          {res.reports.length > 0 && <div className="px-3 pb-1 pt-2 text-xs font-bold uppercase text-muted">{t("Raporlar")}</div>}
          {res.reports.map((r: any) => (
            <button key={r.id} onClick={() => go(`/rapor/${r.id}`)}
              className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface2">
              <span className="truncate"><b>{fmtDate(r.report_date)}</b> · {r.facility ?? "—"}</span>
              <span className="shrink-0 text-muted">{r.member_name}</span>
            </button>
          ))}
          {res.notes.length > 0 && <div className="px-3 pb-1 pt-2 text-xs font-bold uppercase text-muted">{t("Notlar")}</div>}
          {res.notes.map((n: any) => (
            <button key={n.id} onClick={() => go(`/uye/${n.member_id}?sekme=notlar`)}
              className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface2">
              <span className="truncate">{n.text}</span>
              <span className="shrink-0 text-muted">{n.member_name} · {fmtDate(n.date)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [cur, setCur] = useState("");
  const [nw, setNw] = useState("");
  const [err, setErr] = useState<any>(null);
  const [ok, setOk] = useState(false);
  const save = async () => {
    setErr(null);
    try {
      await api("/api/auth/password", { body: { current_password: cur, new_password: nw } });
      setOk(true);
      setCur("");
      setNw("");
    } catch (e) {
      setErr(e);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title={t("Şifre değiştir")}
      footer={<><button className="btn-ghost" onClick={onClose}>{t("Kapat")}</button><button className="btn-primary" onClick={save} disabled={!cur || nw.length < 8}>{t("Kaydet")}</button></>}>
      <div className="space-y-3">
        <Field label={t("Mevcut şifre")}><input type="password" className="input" value={cur} onChange={(e) => setCur(e.target.value)} /></Field>
        <Field label={t("Yeni şifre")} hint={t("En az 8 karakter. Diğer cihazlardaki oturumlar kapatılır.")}><input type="password" className="input" value={nw} onChange={(e) => setNw(e.target.value)} /></Field>
        <ErrorBox error={err} />
        {ok && <div className="rounded-xl bg-okbg px-3 py-2 text-sm text-ok">{t("Şifre güncellendi.")}</div>}
      </div>
    </Modal>
  );
}

function UserMenu() {
  const { me, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [pw, setPw] = useState(false);
  const [tg, setTg] = useState(false);
  const [theme, setTheme] = useState<Theme>(currentTheme());
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  if (!me) return null;
  const pick = (tx: Theme) => {
    setTheme(tx);
    applyTheme(tx);
    api("/api/auth/prefs", { method: "PATCH", body: { theme: tx } }).catch(() => {});
  };
  const fakeMember = me.member ?? { id: me.id, display_name: me.username, avatar_color: null, has_avatar: false, avatar_version: null };
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)} className="rounded-full" aria-label={t("Hesap menüsü")}>
        <Avatar member={fakeMember} size={42} />
      </button>
      {open && (
        <div className="card absolute right-0 top-12 z-40 w-64 p-2">
          <div className="px-3 py-2">
            <div className="font-bold">{me.member?.display_name ?? me.username}</div>
            <div className="text-xs text-muted">@{me.username} · {me.role === "master" ? t("Yönetici") : me.read_only ? t("Üye (salt okunur)") : t("Üye")}</div>
          </div>
          <div className="my-1 border-t border-line" />
          <div className="px-3 pb-1 pt-2 text-xs font-bold uppercase text-muted">{t("Tema")}</div>
          <div className="grid grid-cols-3 gap-1 px-2 pb-2">
            {([["light", <Sun size={15} />, t("Açık")], ["dark", <Moon size={15} />, t("Koyu")], ["system", <Monitor size={15} />, t("Sistem")]] as const).map(([v, ic, l]) => (
              <button key={v} onClick={() => pick(v)} className={`flex flex-col items-center gap-1 rounded-lg py-2 text-xs ${theme === v ? "bg-brandsoft font-bold text-brand" : "hover:bg-surface2"}`}>
                {ic}{l}
              </button>
            ))}
          </div>
          <div className="px-3 pb-1 pt-1 text-xs font-bold uppercase text-muted">{t("Dil")}</div>
          <LangSwitch save className="px-2 pb-2" />
          <button onClick={() => { setTg(true); setOpen(false); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-surface2">
            <Send size={16} className="text-[#2AABEE]" /> {" "}{t("Telegram")}{me.telegram?.linked ? <span className="chip ml-auto bg-okbg text-ok">{t("bağlı")}</span> : <span className="ml-auto text-xs text-muted">{t("bağla")}</span>}
          </button>
          <button onClick={() => { setPw(true); setOpen(false); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-surface2"><KeyRound size={16} /> {" "}{t("Şifre değiştir")}</button>
          <button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-bad hover:bg-badbg"><LogOut size={16} /> {" "}{t("Çıkış yap")}</button>
        </div>
      )}
      <PasswordModal open={pw} onClose={() => setPw(false)} />
      <TelegramModal open={tg} onClose={() => setTg(false)} />
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <Link to="/" className="flex shrink-0 items-center gap-2">
            <Logo size={36} />
            <span className="text-[26px] font-extrabold tracking-tight text-brand">{t("Rimetra")}</span>
          </Link>
          <nav className="mx-auto hidden items-center gap-10 md:flex">
            <NavItem to="/" end icon={<Home size={20} />}>{t("Ailem")}</NavItem>
            <NavItem to="/tahliller" icon={<BarChart3 size={20} />}>{t("Tahliller")}</NavItem>
            <NavItem to="/takvim" icon={<CalendarDays size={20} />}>{t("Takvim")}</NavItem>
          </nav>
          <div className="ml-auto flex flex-1 items-center justify-end gap-3 md:flex-none">
            <div className="hidden w-[340px] sm:block"><SearchBox /></div>
            {me?.role === "master" && (
              <>
                <Link to="/eslesmemis" title={t("Eşleşmemiş testler")} className="hidden rounded-full p-2 text-muted hover:bg-surface2 hover:text-ink lg:block"><Unlink size={21} /></Link>
                <Link to="/yonetim" title={t("Yönetim")} className="rounded-full p-2 text-muted hover:bg-surface2 hover:text-ink"><Settings size={22} /></Link>
              </>
            )}
            <UserMenu />
          </div>
        </div>
        <div className="flex items-center gap-6 overflow-x-auto px-4 pb-3 md:hidden">
          <NavItem to="/" end icon={<Home size={18} />}>{t("Ailem")}</NavItem>
          <NavItem to="/tahliller" icon={<BarChart3 size={18} />}>{t("Tahliller")}</NavItem>
          <NavItem to="/takvim" icon={<CalendarDays size={18} />}>{t("Takvim")}</NavItem>
          {me?.role === "master" && <NavItem to="/eslesmemis" icon={<Unlink size={18} />}>{t("Eşleşmemiş")}</NavItem>}
        </div>
        <div className="px-4 pb-3 sm:hidden"><SearchBox /></div>
      </header>
      <main className="mx-auto max-w-[1500px] px-4 pb-16 pt-6 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}
