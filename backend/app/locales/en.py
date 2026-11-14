"""English translations of backend messages. Key = Turkish source text (placeholders in {braces})."""
from __future__ import annotations

from .en_bot import BOT_EN

MESSAGES_EN: dict[str, str] = {
    # ---------------------------------------------------------------- generic / errors.py / main.py
    "Eksik veya hatalı alan.": "Missing or invalid field.",
    "{what} bulunamadı.": "{what} not found.",
    "Kayıt": "Record",
    "Test": "Test",
    "Skill dosyası": "Skill file",
    "Avatar": "Avatar",
    "PDF": "PDF",
    "Not": "Note",
    "Hatırlatıcı": "Reminder",
    "Üye": "Member",
    "Kullanıcı": "User",
    "API anahtarı": "API key",
    "Rapor": "Report",
    "Uç nokta bulunamadı.": "Endpoint not found.",
    "Rimetra API çalışıyor. Arayüz derlenmemiş (frontend/ → npm run build).":
        "Rimetra API is running. The web interface has not been built (frontend/ → npm run build).",
    "Geçersiz": "Invalid",
    "Geçersiz biçim": "Invalid format",
    "Gerekli": "Required",
    "Boş": "Empty",
    "Bulunamadı": "Not found",
    "Bilinmeyen üye": "Unknown member",
    "Boyut sınırı": "Size limit",
    "PDF bekleniyor": "PDF expected",
    "result_ids veya raw_name": "result_ids or raw_name",
    "Tekrarlanan result_id: {ids}": "Duplicate result_id: {ids}",
    # ---------------------------------------------------------------- auth / deps
    "Çok fazla başarısız deneme. {wait} sn sonra tekrar deneyin.": "Too many failed attempts. Try again in {wait} s.",
    "Kullanıcı adı veya şifre hatalı.": "Incorrect username or password.",
    "Giriş yapmanız gerekiyor.": "You need to sign in.",
    "Mevcut şifre hatalı.": "Current password is incorrect.",
    "Bu işlem için '{scope}' yetkisi gerekli.": "This action requires the '{scope}' permission.",
    "Bu üyeye erişim yetkiniz yok.": "You do not have access to this member.",
    "API anahtarı gerekli (Authorization: Bearer ...).": "An API key is required (Authorization: Bearer ...).",
    "API anahtarı hatalı.": "Invalid API key.",
    "API anahtarı hatalı ya da iptal edilmiş.": "The API key is invalid or has been revoked.",
    "Hız sınırı aşıldı.": "Rate limit exceeded.",
    "Geçersiz istek başlığı.": "Invalid request header.",
    "Bu işlem yalnızca master kullanıcıya açık.": "Only the master user can do this.",
    # ---------------------------------------------------------------- web app api
    "Onay için üyenin adını aynen yazın.": "Type the member's name exactly to confirm.",
    "Master kullanıcının profili silinemez.": "The master user's profile cannot be deleted.",
    "Görsel en fazla 5 MB olabilir.": "The image can be at most 5 MB.",
    "PNG, JPG veya WEBP yükleyin.": "Upload a PNG, JPG or WEBP file.",
    "İki rapor aynı üyeye ait olmalı.": "Both reports must belong to the same member.",
    "Not ekleme yetkiniz yok.": "You are not allowed to add notes.",
    "Bu notu silemezsiniz.": "You cannot delete this note.",
    "Bu test anahtarı zaten var.": "This test key already exists.",
    "Anahtar numune.ad biçiminde olmalı (küçük harf, rakam, _).":
        "The key must be in specimen.name format (lowercase letters, digits, _).",
    "Açıklama en fazla 4000 karakter olabilir.": "The explanation can be at most 4000 characters.",
    "Geçersiz numune.": "Invalid specimen.",
    "Bu kullanıcı adı alınmış.": "This username is taken.",
    "Bu profile zaten bir hesap bağlı.": "An account is already linked to this profile.",
    "Üye hesabı bir profile bağlanmalı.": "A member account must be linked to a profile.",
    "Kendi hesabınızı pasifleştiremezsiniz.": "You cannot deactivate your own account.",
    "Kendi hesabınızı silemezsiniz.": "You cannot delete your own account.",
    "Bilinmeyen yetki: {scopes}": "Unknown permission: {scopes}",
    "Bilinmeyen üye kimliği.": "Unknown member ID.",
    "Telegram botu kapalı. Sunucudaki .env dosyasına TELEGRAM_BOT_TOKEN ekleyin.":
        "The Telegram bot is off. Add TELEGRAM_BOT_TOKEN to the .env file on the server.",
    "Telegram'a ulaşılamadı.": "Could not reach Telegram.",
    "Bot anahtarı (TELEGRAM_BOT_TOKEN) geçersiz.": "The bot token (TELEGRAM_BOT_TOKEN) is invalid.",
    "Telegram sunucusuna bağlanılamadı (internet bağlantısını kontrol edin).":
        "Could not connect to the Telegram server (check the internet connection).",
    "Bu bot başka bir yerde de çalışıyor (aynı token iki sunucuda kullanılamaz).":
        "This bot is also running somewhere else (the same token cannot be used on two servers).",
    "Elle giriş": "Manual entry",
    "Adsız panel": "Untitled panel",
    "{name} kontrolü": "{name} check-up",
    "Sonuç değil": "Not a result",
    # ---------------------------------------------------------------- mcp
    "Rapor gövdesi hatalı.": "Invalid report body.",
    "Gövde hatalı.": "Invalid body.",
    "Bu gövde önizlenmemiş ya da önizleme sonrası değiştirilmiş. Önce preview_report çağırın.":
        "This body was not previewed or was changed after preview. Call preview_report first.",
    "pdf_base64 çözülemedi.": "Could not decode pdf_base64.",
    "Önce preview_result_mappings çağırın.": "Call preview_result_mappings first.",
    "Bilinmeyen araç: {name}": "Unknown tool: {name}",
    # ---------------------------------------------------------------- backup / idempotency
    "Bir yedekleme zaten çalışıyor.": "A backup is already running.",
    "Yedekleme başarısız: {err}": "Backup failed: {err}",
    "Geçersiz yedek adı.": "Invalid backup name.",
    "Yedek bulunamadı.": "Backup not found.",
    "Bu Idempotency-Key farklı bir istek gövdesiyle kullanılmış.":
        "This Idempotency-Key was used with a different request body.",
    # ---------------------------------------------------------------- ingest
    "Üye bulunamadı.": "Member not found.",
    "Belgedeki ad ('{doc}') seçilen üyeyle ('{member}') uyuşmuyor.":
        "The name on the document ('{doc}') does not match the selected member ('{member}').",
    "Belgedeki hasta adı gönderilmedi; isim kontrolü yapılamadı.":
        "The patient name on the document was not sent; the name could not be checked.",
    "Değer '.' (yer tutucu) olduğu için satır atlandı.": "Row skipped because the value is '.' (placeholder).",
    "Ajanın önerdiği '{key}' anahtarıyla eşlendi.": "Matched using the key suggested by the agent: '{key}'.",
    "Aynı test ({key}) aynı numune zamanında raporda iki kez geçiyor; ikincisi eşlenmedi.":
        "The same test ({key}) appears twice in the report at the same sample time; the second was not matched.",
    "Test kataloğa eşlenemedi; 'Eşleşmemiş testler' ekranında bağlanabilir.":
        "The test could not be matched to the catalog; it can be linked on the 'Unmatched tests' screen.",
    "Belgedeki işaret ({src}) ile hesaplanan işaret ({calc}) uyuşmuyor.":
        "The flag on the document ({src}) does not match the computed flag ({calc}).",
    "Raporda kaydedilecek sonuç yok.": "The report has no results to save.",
    "Bu rapor zaten kayıtlı.": "This report is already saved.",
    "Bu sonuç zaten {rid} raporunda var; atlandı.": "This result already exists in report {rid}; skipped.",
    "Raporda eklenecek yeni sonuç kalmadı.": "There are no new results left to add from this report.",
    "Bazı sonuçlar başka bir raporda zaten kayıtlı.": "Some results are already saved in another report.",
    "Bazı sonuçlar eş zamanlı olarak başka raporda kaydedildi.": "Some results were saved in another report at the same time.",
    # ---------------------------------------------------------------- dismiss
    "Ya result_ids ya da raw_name (+ specimen) gönderin.": "Send either result_ids or raw_name (+ specimen).",
    "Bazı sonuçlar bulunamadı.": "Some results were not found.",
    "Bazı sonuçlar zaten gizlenmiş/silinmiş.": "Some results are already hidden/deleted.",
    "Bir teste bağlı sonuçlar gizlenemez; eşleştirmeyi düzeltin ya da raporu silip yeniden girin.":
        "Results linked to a test cannot be hidden; fix the mapping or delete and re-enter the report.",
    "Bu ada sahip eşleşmemiş sonuç bulunamadı.": "No unmatched result with this name was found.",
    "Gizlenmiş sonuç bulunamadı.": "Hidden result not found.",
    "Bu sonuç bir teste bağlı.": "This result is linked to a test.",
    # ---------------------------------------------------------------- ops / mutations
    "Üye kısıtlı anahtar yeni üye oluşturamaz.": "A member-restricted key cannot create new members.",
    "on_overlap 'error' veya 'skip_existing' olmalı.": "on_overlap must be 'error' or 'skip_existing'.",
    "Bu PDF dosyası zaten yüklenmiş.": "This PDF file has already been uploaded.",
    "PDF çok büyük.": "The PDF is too large.",
    "Dosya PDF değil.": "The file is not a PDF.",
    "Bu PDF başka bir rapora zaten eklenmiş.": "This PDF is already attached to another report.",
    "Bilinmeyen test anahtarı.": "Unknown test key.",
    "Geri alma süresi dolmuş.": "The restore period has expired.",
    "Aynı rapor daha sonra yeniden girilmiş.": "The same report was entered again later.",
    "Bazı sonuçlar başka bir raporda kayıtlı.": "Some results are saved in another report.",
    # ---------------------------------------------------------------- remap
    "Numune uyuşmuyor: sonuç '{a}', test '{b}'.": "Specimen mismatch: result '{a}', test '{b}'.",
    "Ölçüm biçimi uyuşmuyor: satırın birimi '{a}', testin birimi '{b}'.":
        "Measurement type mismatch: row unit '{a}', test unit '{b}'.",
    "Hedef test sayısal, ancak satırın değeri sayısal değil.": "The target test is numeric, but the row's value is not.",
    "Önizleme jetonu bu gövdeye ait değil ya da süresi dolmuş. Önce dry_run=true ile yeniden önizleyin.":
        "The preview token does not belong to this body or has expired. Preview again with dry_run=true first.",
    "Aynı sonuç birden fazla kez gönderilmiş.": "The same result was sent more than once.",
    "Bazı sonuçlar bu rapora ait değil ya da bulunamadı.": "Some results do not belong to this report or were not found.",
    "Bazı sonuçlar silinmiş.": "Some results have been deleted.",
    "Hedef test katalogda yok.": "The target test is not in the catalog.",
    "Bazı sonuçların bağlantısı beklenenden farklı; araya başka bir değişiklik girmiş olabilir.":
        "Some results are linked differently than expected; another change may have happened in between.",
    "Hedef test bazı satırlar için uygun değil.": "The target test is not suitable for some rows.",
    "Aynı istekte iki satır aynı teste ve numune zamanına bağlanıyor.":
        "Two rows in the same request are linked to the same test and sample time.",
    "Aynı kişi, test, numune zamanı ve kurum için başka bir kayıt var.":
        "Another record exists for the same person, test, sample time and facility.",
    "Değişiklik sonrası durumda başka kayıtlarla çakışma var.": "After the change, there would be conflicts with other records.",
    "Değişiklik eşzamanlı başka bir kayıtla çakıştı; yeniden önizleyin.":
        "The change conflicted with another simultaneous record; preview again.",
    # ---------------------------------------------------------------- export (CSV / PDF)
    "Kişi": "Person",
    "Kategori": "Category",
    "Test anahtarı": "Test key",
    "Numune zamanı": "Sample time",
    "Değer": "Value",
    "Birim": "Unit",
    "Referans": "Reference",
    "Durum": "Status",
    "Kurum": "Facility",
    "Rapor tarihi": "Report date",
    "Normal": "Normal",
    "Yüksek": "High",
    "Düşük": "Low",
    "Anormal": "Abnormal",
    "Sayfa {n}": "Page {n}",
    "Hazırlanma: {when}  ·  {n} test  ·  Yalnızca değerler ve referans aralıkları; tıbbi yorum içermez.":
        "Prepared: {when}  ·  {n} tests  ·  Values and reference ranges only; no medical interpretation.",
    "Seçilen testler için kayıt bulunamadı.": "No records found for the selected tests.",
    "{cat} (devam)": "{cat} (continued)",
    "Son: {val} {unit}   Ref: {ref}   {status}": "Last: {val} {unit}   Ref: {ref}   {status}",
    "Referans aralığı": "Reference range",
    "Rimetra — {name}": "Rimetra — {name}",
    **BOT_EN,
}
