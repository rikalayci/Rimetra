// İngilizce çeviri kapsamı denetimi: `npm run i18n:check`
// - t("...") ile kullanılan her metnin locales/en.ts içinde karşılığı var mı?
// - t() ile sarılmamış Türkçe JSX metni kaldı mı?
const ts = require("typescript");
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", "src");
const files = [];
(function walk(d) {
  for (const f of fs.readdirSync(d)) {
    const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) walk(p);
    else if (/\.(tsx?|ts)$/.test(f) && !p.includes(`${path.sep}locales${path.sep}`)) files.push(p);
  }
})(SRC);

const enSrc = fs.readFileSync(path.join(SRC, "locales", "en.ts"), "utf8");
const enFile = ts.createSourceFile("en.ts", enSrc, ts.ScriptTarget.Latest, true);
const EN = new Set();
(function v(n) {
  if (ts.isPropertyAssignment(n)) EN.add(ts.isIdentifier(n.name) ? n.name.text : n.name.text);
  ts.forEachChild(n, v);
})(enFile);

// t() ile çalışma anında çevrilen sabit listeler (veri anahtarları)
const DYNAMIC = [
  "Hemogram", "Biyokimya", "Lipid", "Tiroid", "Vitamin ve Mineral", "Diyabet", "İnflamasyon", "Hormon", "Koagülasyon",
  "İdrar", "Seroloji", "Ölçümler", "Eşleşmemiş", "Kan Sayımı", "Kolesterol", "sn", "atım/dk",
];

const CODE_TAGS = new Set(["C", "code", "pre", "kbd"]);
const TR = /[çğıöşüÇĞİÖŞÜ]/;
const missing = new Map();
const unwrapped = [];
const used = new Set(DYNAMIC);
for (const f of files) {
  const sf = ts.createSourceFile(f, fs.readFileSync(f, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const rel = path.relative(SRC, f);
  const where = (n) => `${rel}:${sf.getLineAndCharacterOfPosition(n.getStart()).line + 1}`;
  const visit = (n) => {
    if (ts.isCallExpression(n) && n.expression.getText() === "t") {
      const a = n.arguments[0];
      if (a && (ts.isStringLiteral(a) || ts.isNoSubstitutionTemplateLiteral(a))) {
        used.add(a.text);
        if (!EN.has(a.text)) missing.set(a.text, where(n));
      }
    }
    // t(LISTE[i]) biçimindeki listelerin elemanları
    if ((ts.isArrayLiteralExpression(n)) && n.parent && ts.isVariableDeclaration(n.parent) && /^(MONTHS|DAYS|TOOLS)$/.test(n.parent.name.getText())) {
      for (const e of n.elements) {
        const s = ts.isStringLiteral(e) ? e : ts.isArrayLiteralExpression(e) ? e.elements[1] : null;
        if (s && ts.isStringLiteral(s)) { used.add(s.text); if (!EN.has(s.text)) missing.set(s.text, where(s)); }
      }
    }
    if (ts.isJsxText(n) && TR.test(n.text)) {
      let inCode = false;
      for (let p = n.parent; p; p = p.parent) if (ts.isJsxElement(p) && CODE_TAGS.has(p.openingElement.tagName.getText())) inCode = true;
      if (!inCode) unwrapped.push(`${where(n)}  ${n.text.trim().slice(0, 80)}`);
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
}
for (const k of DYNAMIC) if (!EN.has(k)) missing.set(k, "(dinamik liste)");

let bad = false;
if (missing.size) {
  bad = true;
  console.log(`Çevirisi eksik ${missing.size} metin:`);
  for (const [k, w] of missing) console.log(`  ${w}  ${JSON.stringify(k)}`);
}
if (unwrapped.length) {
  bad = true;
  console.log(`t() ile sarılmamış ${unwrapped.length} Türkçe JSX metni:`);
  unwrapped.forEach((u) => console.log("  " + u));
}
const unused = [...EN].filter((k) => !used.has(k));
if (unused.length) console.log(`(Bilgi) Kullanılmayan ${unused.length} İngilizce anahtar: ${unused.slice(0, 15).map((k) => JSON.stringify(k)).join(", ")}${unused.length > 15 ? " …" : ""}`);
if (!bad) console.log(`Tamam: ${used.size} metnin hepsinin İngilizcesi var.`);
process.exit(bad ? 1 : 0);
