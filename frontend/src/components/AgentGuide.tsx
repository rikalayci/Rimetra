import {
  ArrowRight, Bot, CheckCircle2, Copy, Download, FileText, KeyRound, Laptop, Lightbulb, Server, ShieldCheck, Terminal, TriangleAlert, Wrench,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { t } from "../lib/i18n";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../lib/hooks";
import { Segmented } from "./ui";

type Agent = "codex" | "claude";
type OS = "win" | "unix";

// ------------------------------------------------------------------ küçük yapı taşları

function CodeBlock({ code, label }: { code: string; label?: string }) {
  const [ok, setOk] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(code).then(() => {
      setOk(true);
      setTimeout(() => setOk(false), 1500);
    });
  };
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface2">
      <div className="flex items-center gap-2 border-b border-line px-3 py-1.5 text-xs text-muted">
        <Terminal size={13} /> <span>{label ?? t("Komut")}</span>
        <button onClick={copy} className="ml-auto flex items-center gap-1 rounded-md px-2 py-0.5 font-semibold hover:bg-surface hover:text-ink">
          {ok ? <><CheckCircle2 size={13} className="text-ok" /> {" "}{t("Kopyalandı")}</> : <><Copy size={13} /> {" "}{t("Kopyala")}</>}
        </button>
      </div>
      <pre className="overflow-x-auto px-3 py-2.5 text-[12.5px] leading-relaxed"><code>{code}</code></pre>
    </div>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="relative pl-12">
      <span className="absolute left-0 top-0 flex h-8 w-8 items-center justify-center rounded-full bg-brand text-sm font-extrabold text-white dark:text-[#10201a]">{n}</span>
      <div className="mb-2 pt-1 text-[16px] font-bold">{title}</div>
      <div className="space-y-3 text-sm leading-relaxed text-ink/90">{children}</div>
    </li>
  );
}

function Note({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  const cls = tone === "warn" ? "border-warn/30 bg-warnbg/70" : "border-brand/20 bg-brandsoft/60";
  const Icon = tone === "warn" ? TriangleAlert : Lightbulb;
  return (
    <div className={`flex gap-2 rounded-xl border px-3 py-2 text-sm ${cls}`}>
      <Icon size={16} className={`mt-0.5 shrink-0 ${tone === "warn" ? "text-warn" : "text-brand"}`} /> <div>{children}</div>
    </div>
  );
}

const C = ({ children }: { children: ReactNode }) => <code className="rounded bg-surface2 px-1.5 py-0.5 text-[12.5px]">{children}</code>;

// ------------------------------------------------------------------ içerik üreticileri

function envCommands(os: OS, base: string, key: string) {
  return os === "win"
    ? `setx RIMETRA_URL "${base}"\nsetx RIMETRA_API_KEY "${key}"`
    : `echo 'export RIMETRA_URL="${base}"' >> ~/.bashrc\necho 'export RIMETRA_API_KEY="${key}"' >> ~/.bashrc\nsource ~/.bashrc`;
}

function skillInstall(os: OS, agent: Agent) {
  const dir = agent === "codex" ? ".agents/skills/rimetra-enabiz-import" : ".claude/skills/rimetra-enabiz-import";
  if (os === "win") {
    const wdir = dir.replace(/\//g, "\\");
    return `New-Item -ItemType Directory -Force "$HOME\\${wdir}" | Out-Null\ncurl.exe -sf -H "Authorization: Bearer $env:RIMETRA_API_KEY" "$env:RIMETRA_URL/api/v1/agent/skill" -o "$HOME\\${wdir}\\SKILL.md"`;
  }
  return `mkdir -p ~/${dir}\ncurl -sf -H "Authorization: Bearer $RIMETRA_API_KEY" "$RIMETRA_URL/api/v1/agent/skill" -o ~/${dir}/SKILL.md`;
}

function testCommand(os: OS) {
  return os === "win"
    ? `curl.exe -s -H "Authorization: Bearer $env:RIMETRA_API_KEY" "$env:RIMETRA_URL/api/v1/me"`
    : `curl -s -H "Authorization: Bearer $RIMETRA_API_KEY" "$RIMETRA_URL/api/v1/me"`;
}

const TOOLS: [string, string][] = [
  ["list_members", "Erişebildiği aile üyelerini listeler."],
  ["preview_report", "Raporu kaydetmeden önizler; ne girileceğini, referans dışı ve eşleşmeyen değerleri gösterir. Bir önizleme jetonu döner."],
  ["submit_report", "Raporu kaydeder. Yalnızca önizlenmiş ve değiştirilmemiş gövdeyi, önizleme jetonuyla kabul eder."],
  ["attach_pdf", "Orijinal PDF'i kayıtlı rapora ekler."],
  ["get_member_summary", "Bir üyenin her testinin son değeri ve durumu."],
  ["get_test_history", "Bir testin tüm ölçümleri (ör. ferritin geçmişi)."],
  ["list_reports", "Bir üyenin raporlarını listeler."],
];

// ------------------------------------------------------------------ ana bileşen

export function AgentGuide() {
  const { data: meta } = useApi<any>("/api/app/meta");
  const [, setSp] = useSearchParams();
  const configured: string | undefined = meta?.public_base_url;
  const defaultBase = configured && !/localhost|127\.0\.0\.1/.test(configured) ? configured : window.location.origin;
  const [base, setBase] = useState<string | null>(null);
  const [key, setKey] = useState("");
  const [agent, setAgent] = useState<Agent>("codex");
  const [os, setOs] = useState<OS>(navigator.userAgent.includes("Windows") ? "win" : "unix");

  const url = (base ?? defaultBase).replace(/\/+$/, "");
  const k = key.trim() || t("rmt_live_ANAHTARINIZ");
  const shell = os === "win" ? "PowerShell" : "Terminal";

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------------------------- MCP nedir */}
      <section className="card space-y-4 p-5 sm:p-6">
        <div className="flex items-center gap-2 text-xl font-extrabold"><Bot size={22} className="text-brand" /> {" "}{t("Ajan bağlantısı (MCP)")}</div>
        <p className="max-w-3xl text-[15px] leading-relaxed text-muted">
          {t("MCP (Model Context Protocol), bir yapay zeka ajanının dış sistemlere \"araçlar\" aracılığıyla bağlanmasını sağlayan standarttır. Rimetra kendi içinde bir MCP sunucusu çalıştırır. Codex veya Claude Code'a e-Nabız PDF'ini verdiğinde ajan PDF'i okur, bu araçlarla Rimetra'ya gönderir. Tüm kontroller (mükerrer rapor, isim uyuşmazlığı, yetki)")}{" "}<b>{t("sunucuda")}</b> {" "}{t("yapılır; ajan hata yapsa bile veriyi bozamaz.")}</p>
        <div className="flex flex-col items-stretch gap-2 text-sm sm:flex-row sm:items-center">
          {[
            [<FileText size={18} />, "e-Nabız PDF", t("Bilgisayarındaki dosya")],
            [<Laptop size={18} />, "Codex / Claude Code", t("PDF'i okur, skill kurallarını uygular")],
            [<Server size={18} />, "Rimetra MCP", t("Doğrular, işaretler, kaydeder")],
          ].map(([ic, tx, d], i, arr) => (
            <div key={i} className="flex flex-1 items-center gap-2">
              <div className="flex flex-1 items-center gap-3 rounded-2xl border border-line bg-surface2 px-4 py-3">
                <span className="text-brand">{ic}</span>
                <div><div className="font-bold">{tx as string}</div><div className="text-xs text-muted">{d as string}</div></div>
              </div>
              {i < arr.length - 1 && <ArrowRight size={18} className="hidden shrink-0 text-muted sm:block" />}
            </div>
          ))}
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="rounded-2xl border border-line p-4">
            <div className="mb-2 flex items-center gap-2 font-bold"><Wrench size={16} /> {" "}{t("MCP sunucusu = ajanın elleri")}</div>
            <p className="text-sm text-muted">{t("Veriyi okuyan ve yazan araçları sağlar. Adres:")}{" "}<C>{url}/mcp</C> {" "}{t("· Kimlik:")}{" "}<C>Authorization: Bearer rmt_live_…</C></p>
          </div>
          <div className="rounded-2xl border border-line p-4">
            <div className="mb-2 flex items-center gap-2 font-bold"><FileText size={16} /> {" "}{t("Skill = ajanın kullanım kılavuzu")}</div>
            <p className="text-sm text-muted">{t("e-Nabız PDF'inin nasıl okunacağını (panel başlıkları, sayfaya bölünmüş hücreler,")}{" "}<C>.</C> {" "}{t("satırları) ve iş akışını (önizle → sana özetle → onayla → kaydet → PDF ekle) öğretir.")}</p>
          </div>
        </div>
        <details className="rounded-2xl border border-line p-4">
          <summary className="cursor-pointer font-bold">{t("Araçlar (")}{TOOLS.length})</summary>
          <div className="mt-3 overflow-x-auto">
            <table className="table-clean w-full">
              <tbody>
                {TOOLS.map(([n, d]) => <tr key={n}><td className="whitespace-nowrap font-mono text-xs font-semibold">{n}</td><td className="text-muted">{t(d)}</td></tr>)}
              </tbody>
            </table>
          </div>
        </details>
        <Note tone="warn">
          {t("Rimetra şu an yerel ağda düz HTTP ile çalışıyor. Bu yüzden ajanın")}{" "}<b>{t("aynı ağdaki bir bilgisayarda")}</b> {" "}{t("çalışması gerekir (Codex CLI ve Claude Code böyle çalışır). claude.ai veya ChatGPT web gibi bulut servisleri bu adrese ulaşamaz.")}</Note>
      </section>

      {/* ---------------------------------------------------------------- ayarlar */}
      <section className="card space-y-4 p-5 sm:p-6">
        <div className="text-lg font-extrabold">{t("Kurulum rehberi")}</div>
        <p className="text-sm text-muted">{t("Aşağıdaki iki alanı doldurursan komutlar hazır hale gelir; kopyalayıp yapıştırman yeterli. Anahtar hiçbir yere kaydedilmez, yalnızca bu sayfada komutlara yazılır.")}</p>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="label">{t("Rimetra adresi (ajanın çalıştığı bilgisayardan erişilen)")}</span>
            <input className="input font-mono" value={base ?? defaultBase} onChange={(e) => setBase(e.target.value)} />
            <span className="mt-1 block text-xs text-muted">{t("Sunucu adı çözülmezse sunucunun IP adresini yaz, ör.")}{" "}<C>http://192.168.1.50:8080</C></span>
          </label>
          <label className="block">
            <span className="label">{t("API anahtarı")}</span>
            <input className="input font-mono" placeholder={t("rmt_live_…")} value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" spellCheck={false} />
            <span className="mt-1 block text-xs text-muted">
              {t("Yoksa")}{" "}<button className="font-semibold text-brand underline" onClick={() => setSp({ sekme: "anahtarlar" }, { replace: true })}>{t("API anahtarları")}</button> {" "}{t("sekmesinden oluştur.")}</span>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Segmented<Agent> value={agent} onChange={setAgent} options={[{ value: "codex", label: "Codex" }, { value: "claude", label: "Claude Code" }]} />
          <Segmented<OS> value={os} onChange={setOs} options={[{ value: "win", label: "Windows" }, { value: "unix", label: "Linux / macOS" }]} />
        </div>
      </section>

      {/* ---------------------------------------------------------------- adımlar */}
      <section className="card p-5 sm:p-6">
        <ol className="space-y-8">
          <Step n={1} title={t("API anahtarı oluştur")}>
            <p>{t("Yönetim →")}{" "}<b>{t("API anahtarları")}</b> → <b>{t("Anahtar oluştur")}</b>{t(". Ad:")}{" "}<C>{agent === "codex" ? "Codex" : "Claude Code"}</C>{t(". Yetkiler:")}</p>
            <ul className="ml-5 list-disc text-muted">
              <li><C>reports:read</C>, <C>reports:write</C>, <C>members:read</C> {" "}{t("— PDF girişi için yeterli")}</li>
              <li><C>catalog:write</C> {" "}{t("— yalnızca ajanın eşleşmeyen test adlarını kataloğa bağlamasını istiyorsan")}</li>
            </ul>
            <p>{t("İstersen anahtarı belirli üyelerle sınırla. Anahtar yalnızca bir kez gösterilir; kopyalayıp yukarıdaki alana yapıştır.")}</p>
          </Step>

          <Step n={2} title={t("Ortam değişkenlerini ayarla")}>
            <p>{t("Ajan, PDF'i yüklerken ve skill'i indirirken bu iki değişkeni kullanır")}{agent === "codex" ? t("; Codex ayrıca MCP anahtarını buradan okur") : ""}.</p>
            <CodeBlock label={shell} code={envCommands(os, url, k)} />
            {os === "win" && <Note><C>setx</C> {" "}{t("kalıcıdır ama yalnızca")}{" "}<b>{t("yeni açılan")}</b> {" "}{t("pencerelerde görünür. Komuttan sonra PowerShell'i ve")}{" "}{agent === "codex" ? t("Codex'i") : t("Claude Code'u")} {" "}{t("kapatıp yeniden aç.")}</Note>}
            <p>{t("Bağlantıyı dene; anahtarın adını ve erişebildiği üyeleri döndürmeli:")}</p>
            <CodeBlock label={shell} code={testCommand(os)} />
          </Step>

          {agent === "codex" ? (
            <Step n={3} title={t("MCP sunucusunu Codex'e ekle")}>
              <p>
                {t("Şu dosyayı aç (yoksa oluştur):")}{" "}<C>{os === "win" ? "%USERPROFILE%\\.codex\\config.toml" : "~/.codex/config.toml"}</C> {" "}{t("ve sonuna ekle:")}</p>
              <CodeBlock label={t("config.toml")} code={`[mcp_servers.rimetra]\nurl = "${url}/mcp"\nbearer_token_env_var = "RIMETRA_API_KEY"`} />
              <Note>{t("Anahtarın kendisi bu dosyaya yazılmaz; Codex onu")}{" "}<C>RIMETRA_API_KEY</C> {" "}{t("ortam değişkeninden okur.")}</Note>
            </Step>
          ) : (
            <Step n={3} title={t("MCP sunucusunu Claude Code'a ekle")}>
              <p><C>--scope user</C> {" "}{t("ile her klasörde kullanılabilir olur.")}</p>
              <CodeBlock label={shell} code={`claude mcp add --scope user --transport http rimetra ${url}/mcp --header "Authorization: Bearer ${k}"`} />
            </Step>
          )}

          <Step n={4} title={t("Skill'i kur")}>
            <p>
              {t("Skill, ajana e-Nabız PDF'ini nasıl okuyacağını ve iş akışını öğretir. Bu komut skill'i doğrudan Rimetra'dan indirip")}{" "}
              <C>{agent === "codex" ? "~/.agents/skills/" : "~/.claude/skills/"}</C> {" "}{t("altına koyar:")}</p>
            <CodeBlock label={shell} code={skillInstall(os, agent)} />
            <div className="flex flex-wrap items-center gap-2">
              <a className="btn-ghost btn-sm" href="/api/app/agent/skill?download=1"><Download size={14} /> {" "}{t("SKILL.md'yi indir")}</a>
              <a className="btn-ghost btn-sm" href="/api/app/agent/skill" target="_blank" rel="noreferrer"><FileText size={14} /> {" "}{t("İçeriğe bak")}</a>
              <span className="text-xs text-muted">{t("Elle kurmak istersen dosyayı")}{" "}<C>{agent === "codex" ? "~/.agents/skills/rimetra-enabiz-import/SKILL.md" : "~/.claude/skills/rimetra-enabiz-import/SKILL.md"}</C> {" "}{t("olarak kaydet.")}</span>
            </div>
          </Step>

          <Step n={5} title={t("Kontrol et")}>
            {agent === "codex" ? (
              <>
                <CodeBlock label={shell} code="codex mcp list" />
                <p>{t("Listede")}{" "}<C>rimetra</C> {" "}{t("görünmeli. Codex'i açıp")}{" "}<C>/mcp</C> {" "}{t("yazınca araçlar,")}{" "}<C>/skills</C> {" "}{t("yazınca")}{" "}<C>rimetra-enabiz-import</C> {" "}{t("listelenmeli.")}</p>
              </>
            ) : (
              <>
                <CodeBlock label={shell} code="claude mcp list" />
                <p>{t("Listede")}{" "}<C>rimetra</C> {" "}{t("✓ bağlı görünmeli. Claude Code içinde")}{" "}<C>/mcp</C> {" "}{t("yazınca araçları,")}{" "}<C>/skills</C> {" "}{t("ile skill'i görebilirsin.")}</p>
              </>
            )}
          </Step>

          <Step n={6} title={t("Kullan")}>
            <p>{agent === "codex" ? t("Codex'i") : t("Claude Code'u")} {" "}{t("PDF'lerin bulunduğu klasörde aç ve doğal dille iste:")}</p>
            <CodeBlock
              label={t("Örnek istekler")}
              code={
                agent === "codex"
                  ? t("$rimetra-enabiz-import tahlil_2025-03-12.pdf dosyasını Rimetra'ya gir\n\nBu klasördeki tüm e-Nabız PDF'lerini sırayla Rimetra'ya gir, her birinde önce bana özet göster\n\nRimetra'da Ayşe'nin ferritin geçmişini tablo olarak listele")
                  : t("tahlil_2025-03-12.pdf dosyasını Rimetra'ya gir\n\nBu klasördeki tüm e-Nabız PDF'lerini sırayla Rimetra'ya gir, her birinde önce bana özet göster\n\nRimetra'da Ayşe'nin ferritin geçmişini tablo olarak listele")
              }
            />
            <p className="text-muted">
              {agent === "codex"
                ? <>{t("Skill, istek açıklamasına uyduğunda kendiliğinden devreye girer;")}{" "}<C>$rimetra-enabiz-import</C> {" "}{t("yazarak açıkça da çağırabilirsin.")}</>
                : <>{t("Skill, istek açıklamasına uyduğunda kendiliğinden devreye girer;")}{" "}<C>/rimetra-enabiz-import</C> {" "}{t("yazarak açıkça da çağırabilirsin.")}</>}
            </p>
            <div className="rounded-2xl border border-line p-4">
              <div className="mb-2 font-bold">{t("Ajan sırasıyla şunları yapar")}</div>
              <ol className="ml-5 list-decimal space-y-1 text-muted">
                <li><C>list_members</C> {" "}{t("ile üyeleri alır, PDF'teki adla eşleştirir (emin değilse sana sorar).")}</li>
                <li>{t("PDF'i sayfa sayfa okur; bölünmüş hücreleri birleştirir,")}{" "}<C>.</C> {" "}{t("satırlarını atlar.")}</li>
                <li><C>preview_report</C> {" "}{t("ile önizler ve sana özet gösterir: kaç değer, hangileri referans dışı, hangileri eşleşmedi.")}</li>
                <li>{t("Sen onaylarsan")}{" "}<C>submit_report</C> {" "}{t("ile kaydeder.")}</li>
                <li>{t("Orijinal PDF'i rapora ekler ve rapor kimliğini bildirir.")}</li>
              </ol>
            </div>
            <Note>
              <b>{t("İlk test önerisi:")}</b> {" "}{t("Aynı PDF'i iki kez girmesini iste. İkincisinde \"Bu rapor zaten kayıtlı\" deyip durmalı.")}</Note>
          </Step>
        </ol>
      </section>

      {/* ---------------------------------------------------------------- sorun giderme */}
      <section className="card space-y-3 p-5 sm:p-6">
        <div className="flex items-center gap-2 text-lg font-extrabold"><ShieldCheck size={20} className="text-brand" /> {" "}{t("Sorun giderme")}</div>
        <div className="overflow-x-auto">
          <table className="table-clean w-full min-w-[640px]">
            <thead className="bg-surface2"><tr><th>{t("Belirti")}</th><th>{t("Neden / Çözüm")}</th></tr></thead>
            <tbody>
              <tr><td className="font-semibold">{t("Bağlanamıyor / zaman aşımı")}</td><td className="text-muted">{t("Adres yanlış ya da sunucu adı çözülmüyor → IP adresiyle dene. Sunucuda")}{" "}<C>docker compose ps</C> {" "}{t("ile container'ların çalıştığını kontrol et.")}</td></tr>
              <tr><td className="font-semibold"><C>INVALID_API_KEY</C> (401)</td><td className="text-muted">{t("Anahtar hatalı, iptal edilmiş ya da ortam değişkeni yeni pencereye yansımamış. Terminali/ajanı yeniden aç, 2. adımdaki test komutunu çalıştır.")}</td></tr>
              <tr><td className="font-semibold"><C>SCOPE_DENIED</C> / <C>MEMBER_DENIED</C> (403)</td><td className="text-muted">{t("Anahtarın yetkisi veya üye kısıtı yetersiz. Yeni bir anahtar oluştur.")}</td></tr>
              <tr><td className="font-semibold"><C>NAME_MISMATCH</C> (422)</td><td className="text-muted">{t("PDF'teki ad seçilen üyeyle uyuşmuyor. Üyeler sekmesinde \"Belgedeki ad soyad\" alanını PDF'teki gibi doldur.")}</td></tr>
              <tr><td className="font-semibold"><C>DUPLICATE_REPORT</C> (409)</td><td className="text-muted">{t("Rapor zaten kayıtlı. Bu bir hata değil, koruma; ajan durmalı.")}</td></tr>
              <tr><td className="font-semibold"><C>RATE_LIMITED</C> (429)</td><td className="text-muted">{t("Anahtar başına dakikada 60 istek sınırı aşıldı; kısa bir süre bekle.")}</td></tr>
              <tr><td className="font-semibold">{t("Ajan araçları görmüyor")}</td><td className="text-muted">{agent === "codex" ? <>{t("config.toml'daki tablo adı")}{" "}<C>[mcp_servers.rimetra]</C> {" "}{t("olmalı; Codex'i yeniden başlat.")}</> : <><C>claude mcp list</C> {" "}{t("çıktısını kontrol et; gerekirse")}{" "}<C>claude mcp remove rimetra</C> {" "}{t("ile silip 3. adımı tekrarla.")}</>}</td></tr>
            </tbody>
          </table>
        </div>
        <p className="text-sm text-muted">
          {t("Ayrıntılı REST API dokümanı:")}{" "}<a className="font-semibold text-brand underline" href="/api/docs" target="_blank" rel="noreferrer">{t("/api/docs")}</a> {" "}{t("ve depodaki")}{" "}<C>docs/api.md</C>{t(". Tüm ajan çağrıları")}{" "}<b>{t("Denetim kaydı")}</b> {" "}{t("sekmesinde görünür.")}</p>
      </section>

      {/* ---------------------------------------------------------------- doğrudan REST */}
      <section className="card space-y-3 p-5 sm:p-6">
        <div className="flex items-center gap-2 text-lg font-extrabold"><KeyRound size={18} className="text-brand" /> {" "}{t("MCP olmadan: doğrudan REST API")}</div>
        <p className="text-sm text-muted">{t("Kendi betiğinden veya MCP desteklemeyen bir araçtan gönderim için. Önce")}{" "}<C>dry_run=true</C> {" "}{t("ile önizle, sonra aynı gövdeyi kaydet.")}</p>
        <CodeBlock
          label={shell}
          code={
            os === "win"
              ? `curl.exe -X POST "$env:RIMETRA_URL/api/v1/reports?dry_run=true" \`\n  -H "Authorization: Bearer $env:RIMETRA_API_KEY" \`\n  -H "Content-Type: application/json" \`\n  -H "Idempotency-Key: $([guid]::NewGuid())" \`\n  --data-binary "@rapor.json"`
              : `curl -X POST "$RIMETRA_URL/api/v1/reports?dry_run=true" \\\n  -H "Authorization: Bearer $RIMETRA_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -H "Idempotency-Key: $(uuidgen)" \\\n  --data-binary @rapor.json`
          }
        />
      </section>
    </div>
  );
}
