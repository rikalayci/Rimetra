# Rimetra API

**Temel URL:** `http://<sunucu>:<APP_PORT>/api/v1`  
**Kimlik doğrulama:** `Authorization: Bearer rmt_live_xxxxxxxx…` (Yönetim → API anahtarları)  
**İçerik tipi:** `application/json` (PDF yüklemede `multipart/form-data`)  
**Hız sınırı:** anahtar başına `API_RATE_LIMIT_PER_MINUTE` (varsayılan 60) istek/dk → `429 RATE_LIMITED` + `Retry-After`  
Giriş yapmış kullanıcılar etkileşimli şemayı `/api/docs` adresinde görebilir.

## Yetkiler (scope)

| Scope | İzin |
|---|---|
| `reports:read` | Rapor, özet, geçmiş, katalog okuma |
| `reports:write` | Rapor girişi, PDF ekleme, rapor silme, rapor bazında sonuç eşleştirmesi düzeltme, sonuç olmayan satırları gizleme |
| `members:read` | Üye listesi |
| `members:write` | Üye oluşturma (üye kısıtlı anahtarlar oluşturamaz) |
| `catalog:write` | Ham adı test tanımına bağlama |

Anahtar bir **üye kısıtı** taşıyabilir; kısıt dışındaki üyeye erişim `403 MEMBER_DENIED` döner.

## Uç noktalar

| Metot | Yol | Scope | Açıklama |
|---|---|---|---|
| GET | `/me` | — | Anahtarın adı, yetkileri, erişebildiği üyeler |
| GET | `/members` | `members:read` | Üye listesi |
| POST | `/members` | `members:write` | Yeni üye/profil |
| GET | `/catalog/tests` | `reports:read` | Test tanımları ve alias'lar |
| POST | `/catalog/aliases` | `catalog:write` | `{raw_name, specimen, test_key}` — ham adı bağlar, bekleyen sonuçları eşler |
| POST | `/reports` | `reports:write` | Rapor girişi. Sorgu: `dry_run=true`, `on_overlap=error\|skip_existing`. Başlık: `Idempotency-Key` |
| POST | `/reports/{id}/pdf` | `reports:write` | Orijinal PDF (`file` alanı). Aynı PDF başka rapora eklenemez |
| GET | `/members/{id}/reports` | `reports:read` | `limit`, `offset` ile sayfalı |
| GET | `/reports/{id}` | `reports:read` | Rapor + paneller + sonuçlar |
| GET | `/unmapped` | `reports:read` | Eşleşmemiş sonuçlar, ham ada göre gruplu (`result_ids` ile) |
| POST | `/results/dismiss` | `reports:write` | Sonuç olmayan eşleşmemiş satırları gizler. Sorgu: `dry_run=true` |
| POST | `/results/restore` | `reports:write` | Gizlenmiş satırları geri getirir `{result_ids}` |
| POST | `/reports/{id}/result-mappings` | `reports:write` | Bu rapordaki seçili sonuçların test bağlantısını düzeltir (genel alias'a dokunmaz). Sorgu: `dry_run=true`. Başlık: `Idempotency-Key` |
| DELETE | `/reports/{id}` | `reports:write` | Siler (30 gün içinde arayüzden geri alınabilir) |
| GET | `/members/{id}/tests/{test_key}/history` | `reports:read` | Bir testin tüm ölçümleri + notlar |
| GET | `/members/{id}/summary` | `reports:read` | Her testin son değeri, değişimi, durumu |
| GET | `/agent/skill` | — | Ajan skill dosyası (`SKILL.md`); kurulum komutları buradan indirir |

## Rapor gövdesi — `POST /reports`

Ham metinleri **olduğu gibi** gönderin; ayrıştırma ve işaretleme sunucudadır.

```json
{
  "member_id": "mbr_…",
  "source": "enabiz",
  "report_date": "2025-03-12",
  "facility": "ÖRNEK 12 NOLU AİLE HEKİMLİĞİ BİRİMİ",
  "patient_name_on_document": "BURAK YILMAZ",
  "pdf_sha256": null,
  "panels": [
    {
      "name": "Tam Kan Sayımı (Hemogram)",
      "sample_datetime": "2025-03-12T09:12:00+03:00",
      "specimen": "blood",
      "results": [
        { "raw_name": "Lökosit (WBC)", "raw_value": "3.9", "raw_unit": "10³/µL", "raw_reference": "4.4 - 11.3", "source_flag": "alert" }
      ]
    },
    {
      "name": null,
      "sample_datetime": "2025-03-12T09:12:00+03:00",
      "specimen": "serum",
      "results": [
        { "raw_name": "ALT", "raw_value": "19", "raw_unit": "U/L", "raw_reference": "&lt;41", "source_flag": "ok" }
      ]
    }
  ]
}
```

- `specimen`: `blood | serum | plasma | urine | other`. Test kimliği = **ad + numune** (kandaki “Lökosit” ≠ idrardaki “Lökosit”).
- `source_flag`: PDF'teki yeşil tik → `ok`, kırmızı ünlem → `alert`.
- `sample_datetime` panel başlığındaki zamandır; saat dilimi yoksa `TZ` kabul edilir.
- İsteğe bağlı `results[].test_key`: ajanın eşleme önerisi; yalnızca sunucu eşleyemezse kullanılır.
- TC kimlik numarası **asla** gönderilmez.

### Ayrıştırma kuralları (özet)

| Ham | Sonuç |
|---|---|
| `15.1`, `0,25` | sayısal |
| `>90`, `<0.5` | `value_qualifier` + sayı |
| `Negatif`, `ESER`, `Pozitif (++)` | nitel (`value_text`) |
| `Negatif 0.04`, `Pozitif 1000` | nitel + sayısal |
| `.` | satır atlanır (`SKIPPED_PLACEHOLDER` uyarısı) |
| `Bakteri Bakteri` | `Bakteri` |
| `4.4 - 11.3` / `<41` / `&lt;41` | `ref_low`/`ref_high` (`<x` → x dahil değil) |
| `NEGATİF -`, `- Referans Açıklama : NEGATİF` | `ref_text = NEGATİF` |
| `74 - 106 - Diyabet : ?126 …` | 74–106 + kalanı `ref_note` |
| İdrar dansitesi `1005` | ölçek kuralı → `1.005` |

### Yanıt

`201 Created` (`dry_run=true` ise `200 OK`, kayıt yapılmaz):

```json
{
  "report_id": "rpt_…",
  "dry_run": false,
  "summary": { "results_total": 15, "out_of_range": 7, "unmapped": 0, "flag_mismatches": 2, "skipped": 1 },
  "results": [ { "raw_name": "ALT", "test_key": "serum.alt", "value_numeric": 14, "ref_high": 41, "flag_computed": "normal", "flag_source": "ok", "flag_mismatch": false } ],
  "warnings": [ { "code": "FLAG_MISMATCH", "raw_name": "Eritrosit.", "message": "…" } ]
}
```

Uyarı kodları: `SKIPPED_PLACEHOLDER`, `UNMAPPED`, `FLAG_MISMATCH`, `DUPLICATE_IN_REPORT`, `MAPPED_BY_HINT`, `SKIPPED_EXISTING`, `NO_PATIENT_NAME`.

## Sonuç eşleştirmesi düzeltme — `POST /reports/{id}/result-mappings`

`POST /catalog/aliases` bir ham ada **genel** kural koyar ve yalnızca eşleşmemiş sonuçları bağlar. Yanlış teste bağlanmış
bir sonucu taşımak ya da aynı adın farklı raporlarda farklı anlam taşıdığı durumları düzeltmek için bu uç kullanılır:
değişiklik **sonuç kimliği** üzerinden ve **yalnızca o raporda** yapılır.

```json
{
  "reason": "2021 raporunda mutlak hücre sayımları yanlışlıkla yüzde testlerine bağlanmış.",
  "changes": [
    { "result_id": "res_…", "expected_current_test_key": "blood.baso_pct", "target_test_key": "blood.baso_abs" },
    { "result_id": "res_…", "expected_current_test_key": null,             "target_test_key": "blood.baso_pct" }
  ],
  "preview_token": null
}
```

- `result_id` ve mevcut `test_key` değerleri `GET /reports/{id}` yanıtındaki `results[].id` / `results[].test_key` alanlarından alınır.
- `expected_current_test_key`: sonucun şu anki bağlantısı (eşleşmemişse `null`). Arada değişmişse `409 MAPPING_CHANGED`; yeni durum ezilmez.
- Tüm değişiklikler **tek veritabanı işleminde** uygulanır; biri başarısız olursa hiçbiri uygulanmaz.
- Çakışmalar **değişiklik sonrası nihai duruma** göre denetlenir: aynı istekte sayım yüzde testinden ayrılırken yüzde satırı o teste bağlanabilir.
- Ham veriler (`raw_*`, kaynak işareti, numune zamanı, panel/rapor kimliği, PDF) değişmez. Yalnızca test bağlantısı ve buna bağlı
  gösterim alanları (değer, referans, birim, işaret) ham veriden yeniden hesaplanır; yüzde ↔ sayım gibi değer dönüşümü yapılmaz.
- Uygunluk: hedef test katalogda olmalı, numune grubu uymalı (kan/serum/plazma birbirine uyar), `%` birimli satır yüzde olmayan teste
  (veya tersi) bağlanamaz, sayısal teste sayısal olmayan değer bağlanamaz.
- `?dry_run=true`: hiçbir şey kaydetmeden her satırın `from_test_key`/`to_test_key`, `before`/`after` gösterim değerleri, `changed_count`,
  olası `conflicts[]` (varsa `ok: false`) ve `preview_token` döner. Kaydederken `preview_token` gönderilirse gövde önizlenenle aynı olmalıdır
  (`reason` dahil), yoksa `400 PREVIEW_MISMATCH`.
- `Idempotency-Key` ile tekrarlanan istek ikinci kez işlem yapmaz. Denetim kaydına her satır için `result.remap`
  (anahtar, gerekçe, sonuç kimliği, eski/yeni test) ve rapor için `report.remap_results` yazılır.
- Katalog veya alias değişmediği için `catalog:write` gerekmez; anahtarın üye kısıtı uygulanır.

Hatalar: `403 MEMBER_DENIED`, `404 NOT_FOUND` (rapor yok/silinmiş), `422 RESULT_NOT_IN_REPORT`, `409 RESULT_INACTIVE`,
`409 MAPPING_CHANGED` (`mismatches[]`), `400 UNKNOWN_TEST_KEY`, `422 INCOMPATIBLE_TEST` (`problems[]`), `409 MAPPING_CONFLICT` (`conflicts[]`).

## Sonuç olmayan satırları gizleme — `POST /results/dismiss`

Ajan bazen sonuç olmayan bir satırı (ör. e-Nabız istem satırı `Kan Sayımı Otomatik Hemogram (geniş panel) | Kan | : | 1 | 03.06.2023`)
sonuç diye gönderir; bunlar eşleşmemiş testlerde birikir.

```json
{ "reason": "e-Nabız istem satırı, sonuç değil", "raw_name": "Kan Sayımı Otomatik Hemogram (geniş panel)", "specimen": "blood" }
{ "reason": "e-Nabız istem satırı, sonuç değil", "result_ids": ["res_…"] }
```

- Ya `result_ids` ya da `raw_name` (+ `specimen`) verilir. Ad verilirse anahtarın erişebildiği tüm üyelerdeki, o ad ve numunedeki
  **eşleşmemiş** satırlar gizlenir. `reason` isteğe bağlıdır (varsayılan “Sonuç değil”).
- Kalıcı silme yoktur: satır gizlenir, denetim kaydına `result.dismiss` yazılır. Rapor, PDF ve rapor parmak izi değişmez.
  Gizlenen satırlar rapor ayrıntısında, sayımlarda ve eşleşmemiş listesinde görünmez; rapor silinip geri yüklense de gizli kalır.
- Bir teste bağlı sonuç gizlenemez (`409 RESULT_MAPPED`); onun için eşleştirme düzeltmesi ya da raporu silip yeniden girmek gerekir.
- `?dry_run=true` hiçbir şeyi değiştirmeden gizlenecek satırları döndürür.
- `POST /results/restore` `{ "result_ids": [...] }` gizlenen satırları geri getirir (`result.undismiss`).
- Arayüzde: **Eşleşmemiş testler** ekranındaki göz simgesi (Sonuç değil), ardından çıkan **Geri al**.

## Mükerrer kontrolü

1. **İçerik parmak izi** — üye + kurum + her panel için (numune zamanı + sıralı [numune|normalize ad, değer]). Aynı rapor yeniden indirilip farklı baytlarla gelse bile yakalanır → `409 DUPLICATE_REPORT` (`existing_report_id`).
2. **Sonuç düzeyi** — `UNIQUE(üye, test, numune zamanı, kurum)` → `409 OVERLAPPING_RESULTS` (`conflicts[]`). `on_overlap=skip_existing` ile yalnızca yeni satırlar eklenir.
3. **PDF hash** — `pdf_sha256` alanı veya PDF yüklemesi aynı dosyayı anında yakalar.

`Idempotency-Key` ile tekrarlanan istek aynı yanıtı döner, ikinci kayıt oluşmaz. Aynı anahtar farklı gövdeyle kullanılırsa `409 IDEMPOTENCY_KEY_REUSED`.

## Hatalar

Tümü `{ "error": { "code": "...", "message": "...", ... } }` biçimindedir.

| HTTP | Kod |
|---|---|
| 400 | `VALIDATION_ERROR` (`fields[]`), `UNKNOWN_TEST_KEY`, `PREVIEW_MISMATCH` |
| 401 | `INVALID_API_KEY` |
| 403 | `SCOPE_DENIED`, `MEMBER_DENIED` |
| 404 | `NOT_FOUND` |
| 409 | `DUPLICATE_REPORT`, `OVERLAPPING_RESULTS`, `IDEMPOTENCY_KEY_REUSED`, `MAPPING_CHANGED`, `MAPPING_CONFLICT`, `RESULT_INACTIVE`, `RESULT_MAPPED` |
| 422 | `NAME_MISMATCH` (belgedeki ad üyenin “görünen ad” veya “belgedeki ad soyad” alanıyla uyuşmuyor), `RESULT_NOT_IN_REPORT`, `INCOMPATIBLE_TEST` |
| 429 | `RATE_LIMITED` |

## Önerilen ajan iş akışı

1. `GET /me`, `GET /members`.
2. PDF'teki `Adı/Soyadı` ile üyeyi eşleştir; emin değilsen kullanıcıya sor.
3. PDF'i sayfa sayfa oku; sayfaya bölünmüş hücreleri birleştir (“Bakteri izole” + “edilmedi.”), `.` satırlarını atla.
4. `POST /reports?dry_run=true` → kullanıcıya özetle (kaç değer, hangileri referans dışı, hangileri eşleşmedi).
5. Onay gelirse aynı gövdeyi `Idempotency-Key` ile gönder.
6. `409 DUPLICATE_REPORT` → “Bu rapor zaten kayıtlı” de ve dur; veriyi değiştirerek tekrar deneme.
7. `POST /reports/{id}/pdf` ile orijinal PDF'i ekle.

## MCP

`POST /mcp` (Streamable HTTP, JSON yanıt), aynı Bearer anahtarı.

| Araç | Karşılığı |
|---|---|
| `list_members` | `GET /members` |
| `preview_report` | `POST /reports?dry_run=true` → `preview_token` döner |
| `submit_report` | `POST /reports` — yalnızca aynı gövde + geçerli `preview_token` ile |
| `attach_pdf` | `POST /reports/{id}/pdf` (base64) |
| `get_member_summary` | `GET /members/{id}/summary` |
| `get_test_history` | `GET /members/{id}/tests/{key}/history` |
| `list_reports` | `GET /members/{id}/reports` |
| `get_report` | `GET /reports/{id}` (sonuç kimlikleriyle) |
| `list_unmapped` | `GET /unmapped` |
| `dismiss_results` | `POST /results/dismiss` — `dry_run` varsayılanı `true` |
| `restore_results` | `POST /results/restore` |
| `preview_result_mappings` | `POST /reports/{id}/result-mappings?dry_run=true` → `preview_token` döner |
| `apply_result_mappings` | `POST /reports/{id}/result-mappings` — yalnızca aynı gövde + geçerli `preview_token` ile |

Adım adım kurulum (Codex ve Claude Code için ayrı) uygulamada **Yönetim → Ajan bağlantısı (MCP)** sekmesindedir.

Claude Code örneği:

```bash
claude mcp add --transport http rimetra http://<sunucu>:8080/mcp \
  --header "Authorization: Bearer rmt_live_…"
```

## Örnek

```bash
curl -X POST "http://<sunucu>:8080/api/v1/reports?dry_run=true" \
  -H "Authorization: Bearer $RIMETRA_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d @rapor.json
```
