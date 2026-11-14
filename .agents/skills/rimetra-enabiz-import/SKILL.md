---
name: rimetra-enabiz-import
description: Use when the user gives an e-Nabız lab-result PDF and asks to enter it into Rimetra (the family lab tracker) via its MCP server or API. Not for general medical questions.
---

# Rimetra — e-Nabız PDF girişi

Rimetra, ailenin tahlil sonuçlarını saklayan, kullanıcının kendi sunucusunda çalışan uygulamadır. Bu skill bir e-Nabız PDF'ini okuyup Rimetra'ya **doğru, eksiksiz ve mükerrer olmadan** girmeyi anlatır.

Araçlar: `rimetra` MCP sunucusu (`list_members`, `preview_report`, `submit_report`, `attach_pdf`, `get_member_summary`, `get_test_history`, `list_reports`, `get_report`, `list_unmapped`, `dismiss_results`, `restore_results`, `preview_result_mappings`, `apply_result_mappings`).
Ortam değişkenleri: `RIMETRA_URL` (ör. `http://192.168.1.50:8080`) ve `RIMETRA_API_KEY` (`rmt_live_…`).

## Temel kurallar

- **TC kimlik numarasını asla gönderme, asla yazma, asla tekrar etme.**
- Tıbbi yorum veya teşhis yapma. Sadece değeri, referansı ve durumu aktar.
- Değerleri **ham metin olarak, PDF'te yazdığı gibi** gönder (`raw_*` alanları). Ayrıştırma ve işaretleme kararı sunucunundur; sen yeniden yorumlama, birim çevirme, yuvarlama.
- Emin olmadığın hiçbir şeyi tahmin etme; kullanıcıya sor.
- `DUPLICATE_REPORT` gelirse dur. Veriyi değiştirerek tekrar deneme.

## İş akışı

1. **Üyeleri al:** `list_members`.
2. **Kişiyi eşleştir:** PDF başlığındaki `Adı/Soyadı` ile üyelerin `display_name` / `full_name` alanlarını karşılaştır. Tek ve açık bir eşleşme yoksa kullanıcıya hangi üye olduğunu sor.
3. **PDF'i sayfa sayfa oku** ve aşağıdaki ayrıştırma kurallarına göre gövdeyi hazırla.
4. **PDF hash'ini hesapla** ve gövdeye `pdf_sha256` olarak ekle (aynı dosya daha önce yüklendiyse sunucu anında yakalar):
   - Windows PowerShell: `(Get-FileHash "<dosya.pdf>" -Algorithm SHA256).Hash.ToLower()`
   - Linux/macOS: `sha256sum "<dosya.pdf>"`
5. **Önizle:** `preview_report` ile gövdeyi gönder.
6. **Kullanıcıya özetle** (kısa):
   - kişi, rapor tarihi, kurum
   - kaç değer girilecek, kaç satır atlandı
   - referans dışı olanlar (test adı, değer, referans)
   - eşleşmeyen testler (`unmapped`) ve işaret uyuşmazlıkları (`flag_mismatch`)
   - varsa uyarılar
   Sonra "Kaydedeyim mi?" diye sor.
7. **Onay gelirse kaydet:** `submit_report` ile **önizlenen gövdenin aynısını** ve dönen `preview_token`'ı gönder. Ağ hatasında tekrar denerken aynı `idempotency_key`'i kullan (ilk denemede bir UUID üret).
8. **Orijinal PDF'i ekle.** Büyük dosyayı base64 ile araca vermek yerine REST ile yükle:
   - PowerShell:
     ```powershell
     curl.exe -s -X POST "$env:RIMETRA_URL/api/v1/reports/<report_id>/pdf" -H "Authorization: Bearer $env:RIMETRA_API_KEY" -F "file=@<dosya.pdf>;type=application/pdf"
     ```
   - bash:
     ```bash
     curl -s -X POST "$RIMETRA_URL/api/v1/reports/<report_id>/pdf" -H "Authorization: Bearer $RIMETRA_API_KEY" -F "file=@<dosya.pdf>;type=application/pdf"
     ```
   Shell kullanılamıyorsa `attach_pdf` aracını base64 ile kullan.
9. **Bitir:** Kaydedilen rapor kimliğini ve referans dışı sayısını tek cümleyle bildir.

## Hata durumları

| Kod | Yapılacak |
|---|---|
| `DUPLICATE_REPORT` | "Bu rapor zaten kayıtlı" de, `existing_report_id`'yi göster, dur. |
| `OVERLAPPING_RESULTS` | Çakışan testleri listele. Kullanıcı isterse aynı gövdeyi `on_overlap: "skip_existing"` ile yeniden önizle (önizleme jetonu bu ayarla birlikte geçerlidir). |
| `NAME_MISMATCH` | Belgedeki ad ile seçilen üye uyuşmuyor. Kullanıcıya sor; doğru üye seçilmişse Rimetra'da o üyenin "Belgedeki ad soyad" alanının güncellenmesi gerekir. |
| `PREVIEW_REQUIRED` | Gövde önizlemeden sonra değişmiş. Yeniden önizle. |
| `VALIDATION_ERROR` | `fields` listesindeki alanları düzelt, yeniden önizle. |
| `INVALID_API_KEY` / `SCOPE_DENIED` / `MEMBER_DENIED` | Kullanıcıya anahtarın veya yetkisinin uygun olmadığını söyle, dur. |

## Gövde biçimi

```json
{
  "member_id": "mbr_…",
  "source": "enabiz",
  "report_date": "YYYY-MM-DD",
  "facility": "Sağlık Tesisi alanı aynen",
  "patient_name_on_document": "Adı/Soyadı alanı aynen",
  "pdf_sha256": "64 karakter hex",
  "panels": [
    {
      "name": "Tam Kan Sayımı (Hemogram)",
      "sample_datetime": "2025-03-12T09:12:00+03:00",
      "specimen": "blood",
      "results": [
        { "raw_name": "Lökosit (WBC)", "raw_value": "3.9", "raw_unit": "10³/µL", "raw_reference": "4.4 - 11.3", "source_flag": "alert" }
      ]
    }
  ]
}
```

## e-Nabız PDF ayrıştırma kuralları

**Başlık:** `Adı/Soyadı` → `patient_name_on_document`; `Tarih` → `report_date`; `Sağlık Tesisi` → `facility`. Cinsiyet ve doğum tarihi gönderilmez. TC kimlik no gönderilmez.

**Paneller:** Tablodaki gri satırlar panel başlığıdır, ör. `12.03.2025 09:12 | Tam Kan Sayımı (Hemogram)`.
- Başlıktaki tarih-saat **numune zamanıdır** → `sample_datetime` (Türkiye saati, `+03:00`). Rapor tarihinden farklı olabilir; panel başlığındakini kullan.
- Panel adı boşsa `name: null` gönder (uydurma ad verme).
- `specimen`: Hemogram, HbA1c, koagülasyon, kan grubu → `blood`; biyokimya, lipid, tiroid, hormon, vitamin, seroloji → `serum`; idrar tetkiki, mikroskopi, idrar kültürü → `urine`; emin değilsen panelin içeriğine göre seç.

**Test adları:**
- Adı PDF'te yazdığı gibi gönder.
- e-Nabız bazı adları iki kez yazar ("Bakteri Bakteri", "# Lenfosit # Lenfosit"). Olduğu gibi gönderebilirsin; sunucu tek yarıya indirir.
- Aynı ad farklı panellerde farklı testtir (kandaki "Lökosit" ≠ idrardaki "Lökosit"). Her sonucu kendi paneline koy.

**Değerler (`raw_value`):**
- Hücrede ne yazıyorsa onu gönder: `15.1`, `0,25`, `>90`, `<0.5`, `Negatif`, `ESER`, `Pozitif (++)`, `POZİTİF (++++)`, `Negatif 0.04`, `AB Rh(-)`.
- Değeri yalnızca `.` olan satırları **atla** (gönderme).
- **İstem (tetkik isteği) satırlarını atla.** e-Nabız bazı raporlarda istenen tetkikleri ayrı bir satırda listeler:
  `Kan Sayımı Otomatik Hemogram (geniş panel) | Kan | : | 1 | 03.06.2023`. Bu bir sonuç değildir: adın yanında numune türü
  (Kan, İdrar, Serum…), değer yerinde adet (`1`, `2`) ve bir tarih bulunur, birim ve referans yoktur. Bu satırları gönderme.
  Panel adı gibi görünüyorsa panelin `name` alanında kullanabilirsin. Emin değilsen önizlemede kullanıcıya sor.
- **Sayfa bölünmesi:** Bir hücrenin metni sonraki sayfada devam edebilir (ör. 1. sayfa "Bakteri izole", 2. sayfa "edilmedi."). Bu parçaları **birleştir** → "Bakteri izole edilmedi." Birleştirmezsen anlam tersine döner. Her sayfanın ilk satırlarını, önceki sayfanın son satırının devamı olup olmadığı açısından kontrol et.

**Birim (`raw_unit`):** Aynen gönder; yoksa `null`.

**Referans (`raw_reference`):** Aynen gönder. Örnekler: `4.4 - 11.3`, `<41`, `&lt;41`, `NEGATİF -`, `- Referans Açıklama : NEGATİF`, `74 - 106 - Diyabet : ?126 ...` (bozuk karakterleri düzeltme, olduğu gibi gönder). Boşsa `null`.

**İşaret (`source_flag`):** Yeşil tik → `"ok"`, kırmızı ünlem → `"alert"`, işaret yoksa `null`. Bu sadece kaynak bilgisidir; asıl durumu sunucu hesaplar. Uyuşmazlık olursa önizlemede `flag_mismatch: true` görünür, kullanıcıya belirt.

## Sonradan düzeltme

Yalnızca kullanıcı isterse ve her zaman önce önizleyip onay alarak:

- **Sonuç olmayan satır kaydedilmişse** (ör. istem satırı eşleşmemiş testlerde görünüyorsa): `list_unmapped` ile `result_ids`'i bul,
  `dismiss_results` ile önce `dry_run: true`, onay gelince `dry_run: false` gönder. Kalıcı silmez; `restore_results` ile geri alınır.
  Bir teste bağlı sonuçlar bu yolla gizlenemez.
- **Sonuç yanlış teste bağlanmışsa** (ör. sayım yüzde testine): genel alias'ı değiştirme. `get_report` ile sonuç kimliklerini al,
  `preview_result_mappings` ile önizle, onay gelince aynı gövdeyi `preview_token` ile `apply_result_mappings`'e gönder.

## Kontrol listesi (göndermeden önce)

- [ ] Doğru üye seçildi (emin değilsem sordum).
- [ ] TC kimlik numarası hiçbir alanda yok.
- [ ] Her panelin `sample_datetime`'ı panel başlığından alındı.
- [ ] `.` değerli satırlar ve istem satırları (`Kan | : | 1 | tarih`) atlandı.
- [ ] Sayfaya bölünmüş hücreler birleştirildi.
- [ ] Tüm sayfalardaki tüm satırlar dahil edildi (satır sayısını PDF ile karşılaştır).
- [ ] Önizleme özeti kullanıcıya gösterildi ve onay alındı.
