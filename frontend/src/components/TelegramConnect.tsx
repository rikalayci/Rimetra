import { Bell, BellOff, CheckCircle2, ExternalLink, Loader2, Send, Unlink } from "lucide-react";
import { t } from "../lib/i18n";
import qrcode from "qrcode-generator";
import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDateTime } from "../lib/format";
import { ErrorBox, Modal, Spinner } from "./ui";

export interface TelegramStatus {
  enabled: boolean;
  running: boolean;
  bot_username: string | null;
  bot_name: string | null;
  bot_url: string | null;
  last_error: string | null;
  notify_enabled: boolean;
  linked: boolean;
  username: string | null;
  linked_at: string | null;
  notify: boolean;
}

function Qr({ text }: { text: string }) {
  const svg = useMemo(() => {
    const q = qrcode(0, "M");
    q.addData(text);
    q.make();
    return q.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
  }, [text]);
  return <div className="mx-auto w-44 rounded-xl bg-white p-1 [&>svg]:h-auto [&>svg]:w-full" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export function BotSetupSteps() {
  return (
    <ol className="list-decimal space-y-1.5 pl-5 text-sm">
      <li>{t("Telegram'da")}{" "}<a className="font-semibold text-brand underline" href="https://t.me/BotFather" target="_blank" rel="noreferrer">{t("@BotFather")}</a>{t("'a yazın →")}{" "}<code>/newbot</code> {" "}{t("→ bota bir ad ve")}{" "}<code>…bot</code> {" "}{t("ile biten bir kullanıcı adı verin (ör.")}{" "}<code>RimetraAileBot</code>).</li>
      <li>{t("BotFather'ın verdiği anahtarı (")}<code>123456:ABC…</code>{t(") sunucudaki")}{" "}<code>.env</code> {" "}{t("dosyasına ekleyin:")}{" "}<pre className="mt-1 overflow-x-auto rounded-lg bg-surface2 p-2 text-xs">TELEGRAM_BOT_TOKEN=123456:ABC...</pre></li>
      <li>{t("Uygulamayı yeniden başlatın:")}{" "}<code>docker compose up -d</code> {" "}{t("(Portainer'da stack →")}{" "}<b>{t("Update")}</b>).</li>
      <li>{t("Buraya dönüp")}{" "}<b>{t("Telegram'ı bağla")}</b>{t("'ya dokunun.")}</li>
    </ol>
  );
}

export function TelegramModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { me, refresh } = useAuth();
  const [st, setSt] = useState<TelegramStatus | null>(null);
  const [link, setLink] = useState<{ url: string; code: string; expires_in: number } | null>(null);
  const [err, setErr] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const s = await api<TelegramStatus>("/api/app/telegram");
      setSt(s);
      return s;
    } catch (e) {
      setErr(e);
      return null;
    }
  };

  useEffect(() => {
    if (!open) return;
    setLink(null);
    setErr(null);
    load();
  }, [open]);

  // bağlantı bekleniyorken durumu yokla; bağlanınca otomatik ilerle
  useEffect(() => {
    if (!open || !link || st?.linked) return;
    const tx = setInterval(async () => {
      const s = await load();
      if (s?.linked) {
        setLink(null);
        refresh();
      }
    }, 2500);
    return () => clearInterval(tx);
  }, [open, link, st?.linked]);

  const start = async () => {
    setBusy(true);
    setErr(null);
    try {
      const l = await api<{ url: string; code: string; expires_in: number }>("/api/app/telegram/link", { method: "POST" });
      setLink(l);
      window.open(l.url, "_blank", "noopener");
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  const toggleNotify = async () => {
    if (!st) return;
    setSt(await api<TelegramStatus>("/api/app/telegram", { method: "PATCH", body: { notify: !st.notify } }));
  };
  const unlink = async () => {
    if (!confirm(t("Telegram bağlantısı kaldırılsın mı? Bot artık size yanıt vermez."))) return;
    setSt(await api<TelegramStatus>("/api/app/telegram", { method: "DELETE" }));
    refresh();
  };
  const master = me?.role === "master";

  return (
    <Modal open={open} onClose={onClose} title={<span className="flex items-center gap-2"><Send size={18} className="text-[#2AABEE]" /> {" "}{t("Telegram")}</span>}>
      {!st ? <Spinner /> : !st.enabled ? (
        <div className="space-y-3">
          <p className="text-sm">{t("Sonuçlarınıza Telegram'dan da bakabilirsiniz: son tahlil, referans dışı değerler, test grafikleri ve yeni tahlil bildirimleri.")}</p>
          {master ? (<><div className="font-bold">{t("Botu açmak için (bir kerelik)")}</div><BotSetupSteps /></>) : (
            <div className="rounded-xl bg-surface2 px-3 py-2 text-sm text-muted">{t("Telegram botu henüz açılmamış. Yöneticiden açmasını isteyin.")}</div>
          )}
        </div>
      ) : st.linked ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-xl bg-okbg px-3 py-3 text-ok">
            <CheckCircle2 size={22} />
            <div className="text-sm"><b>{t("Bağlı")}</b>{st.username && <> · @{st.username}</>}{st.linked_at && <div className="text-xs opacity-80">{fmtDateTime(st.linked_at)}</div>}</div>
          </div>
          {st.bot_url && (
            <a className="btn-primary w-full justify-center" href={st.bot_url} target="_blank" rel="noreferrer"><ExternalLink size={16} /> @{st.bot_username} {" "}{t("sohbetini aç")}</a>
          )}
          <div className="rounded-xl border border-line p-3 text-sm">
            <div className="mb-1 font-bold">{t("Botta neler yapabilirsiniz?")}</div>
            <ul className="list-disc space-y-0.5 pl-5 text-muted">
              <li>{t("Alttaki butonlar: referans dışı değerler, son rapor, raporlar, tüm değerler, kontroller")}</li>
              <li>{t("Test adı yazın (ör.")}{" "}<i>{t("ferritin")}</i>, <i>{t("ayşe b12")}</i>{t(") → geçmişi grafikle gelir")}</li>
              <li>{t("Doktor için PDF özeti ve raporun orijinal PDF'i")}</li>
              <li>{t("Yeni tahlil eklenince bildirim")}</li>
            </ul>
          </div>
          <button className="btn-ghost w-full justify-center" onClick={toggleNotify}>
            {st.notify ? <><BellOff size={16} /> {" "}{t("Yeni tahlil bildirimlerini kapat")}</> : <><Bell size={16} /> {" "}{t("Yeni tahlil bildirimlerini aç")}</>}
          </button>
          <button className="btn-ghost w-full justify-center text-bad" onClick={unlink}><Unlink size={16} /> {" "}{t("Bağlantıyı kaldır")}</button>
          <p className="text-xs text-muted">{t("Not: Telegram bot sohbetleri uçtan uca şifreli değildir; mesajlar Telegram sunucularından geçer.")}</p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm">{t("Hesabınızı Telegram'a bağlayın; sonuçlarınızı oradan, kendi yetkinizle görün")}{master ? t(" (yönetici olarak tüm aile)") : ""}.</p>
          {!link ? (
            <button className="btn-primary w-full justify-center py-3 text-base" onClick={start} disabled={busy}>
              <Send size={18} /> {busy ? t("Hazırlanıyor…") : t("Telegram'ı bağla")}
            </button>
          ) : (
            <div className="space-y-3 text-center">
              <a className="btn-primary w-full justify-center py-3 text-base" href={link.url} target="_blank" rel="noreferrer"><ExternalLink size={18} /> {" "}{t("Telegram'da aç")}</a>
              <div className="text-sm text-muted">{t("Açılan sohbette")}{" "}<b>{t("BAŞLAT")}</b>{t("'a dokunun. Bilgisayardaysanız telefonunuzla okutun:")}</div>
              <Qr text={link.url} />
              <div className="flex items-center justify-center gap-2 text-sm text-muted"><Loader2 size={16} className="animate-spin" /> {" "}{t("Bağlantı bekleniyor… (15 dk geçerli)")}</div>
            </div>
          )}
          {st.last_error && <ErrorBox error={{ message: st.last_error }} />}
          <ErrorBox error={err} />
        </div>
      )}
    </Modal>
  );
}
