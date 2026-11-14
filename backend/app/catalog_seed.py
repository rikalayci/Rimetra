"""Yerleşik test kataloğu. Uygulama her açılışta eksik olanları ekler (var olanlara dokunmaz).

Test kimliği = isim + numune tipi. "Lökosit" kanda ve idrarda iki ayrı testtir.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .catalog_info import CATALOG_INFO
from .models import TestAlias, TestDefinition
from .parsing import normalize_alias

DENSITY_RULE = [{"if_gt": 100, "factor": 0.001}]

# (key, görünen ad, numune, kategori, birim, değer tipi, [alias'lar], ölçek kuralı)
CATALOG: list[tuple] = [
    # ---------------- Hemogram (tam kan) ----------------
    ("blood.wbc", "Lökosit (WBC)", "blood", "Hemogram", "10³/µL", "numeric", ["Lökosit (WBC)", "Lökosit", "WBC", "Beyaz Küre"], None),
    ("blood.rbc", "Eritrosit (RBC)", "blood", "Hemogram", "10⁶/µL", "numeric", ["Eritrosit (RBC)", "Eritrosit", "RBC"], None),
    ("blood.hgb", "Hemoglobin (Hb)", "blood", "Hemogram", "g/dL", "numeric", ["Hemoglobin (Hb)", "Hemoglobin", "HGB", "Hb"], None),
    ("blood.hct", "Hematokrit (Hct)", "blood", "Hemogram", "%", "numeric", ["Hematokrit (Hct)", "Hematokrit", "HCT"], None),
    ("blood.mcv", "MCV", "blood", "Hemogram", "fL", "numeric", ["MCV", "Ortalama Eritrosit Hacmi"], None),
    ("blood.mch", "MCH", "blood", "Hemogram", "pg", "numeric", ["MCH"], None),
    ("blood.mchc", "MCHC", "blood", "Hemogram", "g/dL", "numeric", ["MCHC"], None),
    ("blood.rdw", "RDW", "blood", "Hemogram", "%", "numeric", ["RDW", "RDW-CV", "RDW CV"], None),
    ("blood.rdw_sd", "RDW-SD", "blood", "Hemogram", "fL", "numeric", ["RDW-SD", "RDW SD"], None),
    ("blood.plt", "Trombosit (PLT)", "blood", "Hemogram", "10³/µL", "numeric", ["Trombosit (PLT)", "Trombosit", "PLT"], None),
    ("blood.mpv", "MPV", "blood", "Hemogram", "fL", "numeric", ["MPV"], None),
    ("blood.pct", "Plateletkrit (PCT)", "blood", "Hemogram", "%", "numeric", ["PCT", "Plateletkrit", "Trombokrit"], None),
    ("blood.pdw", "PDW", "blood", "Hemogram", "%", "numeric", ["PDW"], None),
    ("blood.neu_abs", "# Nötrofil", "blood", "Hemogram", "10³/µL", "numeric", ["# Nötrofil", "#Nötrofil", "NEU#", "Nötrofil#", "Nötrofil Sayısı"], None),
    ("blood.lym_abs", "# Lenfosit", "blood", "Hemogram", "10³/µL", "numeric", ["# Lenfosit", "#Lenfosit", "LYM#", "Lenfosit#", "Lenfosit Sayısı"], None),
    ("blood.mono_abs", "# Monosit", "blood", "Hemogram", "10³/µL", "numeric", ["# Monosit", "#Monosit", "MONO#", "Monosit#"], None),
    ("blood.eos_abs", "# Eozinofil", "blood", "Hemogram", "10³/µL", "numeric", ["# Eozinofil", "#Eozinofil", "EOS#", "Eozinofil#"], None),
    ("blood.baso_abs", "# Bazofil", "blood", "Hemogram", "10³/µL", "numeric", ["# Bazofil", "#Bazofil", "BASO#", "Bazofil#"], None),
    ("blood.neu_pct", "% Nötrofil", "blood", "Hemogram", "%", "numeric", ["% Nötrofil", "%Nötrofil", "NEU%", "Nötrofil%", "Nötrofil %", "Nötrofil"], None),
    ("blood.lym_pct", "% Lenfosit", "blood", "Hemogram", "%", "numeric", ["% Lenfosit", "%Lenfosit", "LYM%", "Lenfosit%", "Lenfosit %", "Lenfosit"], None),
    ("blood.mono_pct", "% Monosit", "blood", "Hemogram", "%", "numeric", ["% Monosit", "%Monosit", "MONO%", "Monosit%", "Monosit %", "Monosit"], None),
    ("blood.eos_pct", "% Eozinofil", "blood", "Hemogram", "%", "numeric", ["% Eozinofil", "%Eozinofil", "EOS%", "Eozinofil%", "Eozinofil %", "Eozinofil"], None),
    ("blood.baso_pct", "% Bazofil", "blood", "Hemogram", "%", "numeric", ["% Bazofil", "%Bazofil", "BASO%", "Bazofil%", "Bazofil %", "Bazofil"], None),
    ("blood.mentzer", "Mentzer İndeksi", "blood", "Hemogram", None, "numeric", ["Mentzer İndeksi", "Mentzer Indeksi", "Mentzer"], None),
    ("blood.esr", "Sedimantasyon", "blood", "İnflamasyon", "mm/saat", "numeric", ["Sedimantasyon", "Eritrosit Sedimantasyon Hızı", "Eritrosit Sedimentasyon Hızı", "Eritrosit sedimentasyon hızı (ESR)", "Eritrosit Sedimantasyon Hızı (ESH)", "Sedimentasyon", "ESH", "ESR", "Sedim"], None),
    # ---------------- Biyokimya ----------------
    ("serum.glucose", "Glukoz (açlık)", "serum", "Biyokimya", "mg/dL", "numeric", ["Glukoz", "Glukoz (Açlık)", "Açlık Kan Şekeri", "Açlık Glukozu", "Glikoz"], None),
    ("serum.urea", "Üre", "serum", "Biyokimya", "mg/dL", "numeric", ["Üre", "Ure"], None),
    ("serum.bun", "BUN", "serum", "Biyokimya", "mg/dL", "numeric", ["BUN", "Kan Üre Azotu", "Üre Azotu", "Üre Nitrojeni", "Kan Üre Nitrojeni"], None),
    ("serum.creatinine", "Kreatinin", "serum", "Biyokimya", "mg/dL", "numeric", ["Kreatinin", "Creatinine"], None),
    ("serum.egfr", "eGFR", "serum", "Biyokimya", "mL/dk/1.73m²", "numeric", ["eGFR", "GFR", "Tahmini GFR", "eGFR (CKD-EPI)", "tGFH", "Tahmini GFH", "GFH", "Tahmini Glomerüler Filtrasyon Hızı"], None),
    ("serum.uric_acid", "Ürik Asit", "serum", "Biyokimya", "mg/dL", "numeric", ["Ürik Asit", "Ürik asit"], None),
    ("serum.alt", "ALT", "serum", "Biyokimya", "U/L", "numeric", ["ALT", "Alanin Aminotransferaz", "SGPT", "ALT (SGPT)"], None),
    ("serum.ast", "AST", "serum", "Biyokimya", "U/L", "numeric", ["AST", "Aspartat Aminotransferaz", "SGOT", "AST (SGOT)"], None),
    ("serum.ggt", "GGT", "serum", "Biyokimya", "U/L", "numeric", ["GGT", "Gama Glutamil Transferaz"], None),
    ("serum.alp", "ALP", "serum", "Biyokimya", "U/L", "numeric", ["ALP", "Alkalen Fosfataz"], None),
    ("serum.ldh", "LDH", "serum", "Biyokimya", "U/L", "numeric", ["LDH", "Laktat Dehidrogenaz"], None),
    ("serum.bili_total", "Total Bilirubin", "serum", "Biyokimya", "mg/dL", "numeric", ["Total Bilirubin", "Bilirubin (Total)", "Bilirubin Total", "Bilirubin, Total", "T.Bilirubin"], None),
    ("serum.bili_direct", "Direkt Bilirubin", "serum", "Biyokimya", "mg/dL", "numeric", ["Direkt Bilirubin", "Bilirubin (Direkt)", "Bilirubin Direkt", "Bilirubin, Direkt", "D.Bilirubin"], None),
    ("serum.total_protein", "Total Protein", "serum", "Biyokimya", "g/dL", "numeric", ["Total Protein", "Protein (Total)"], None),
    ("serum.albumin", "Albümin", "serum", "Biyokimya", "g/dL", "numeric", ["Albümin", "Albumin"], None),
    ("serum.sodium", "Sodyum (Na)", "serum", "Biyokimya", "mmol/L", "numeric", ["Sodyum", "Sodyum (Na)", "Na"], None),
    ("serum.potassium", "Potasyum (K)", "serum", "Biyokimya", "mmol/L", "numeric", ["Potasyum", "Potasyum (K)", "K"], None),
    ("serum.chloride", "Klor (Cl)", "serum", "Biyokimya", "mmol/L", "numeric", ["Klor", "Klorür", "Klor (Cl)", "Cl"], None),
    ("serum.calcium", "Kalsiyum (Ca)", "serum", "Biyokimya", "mg/dL", "numeric", ["Kalsiyum", "Kalsiyum (Ca)", "Ca"], None),
    ("serum.phosphorus", "Fosfor", "serum", "Biyokimya", "mg/dL", "numeric", ["Fosfor", "Fosfor (P)", "İnorganik Fosfor"], None),
    ("serum.magnesium", "Magnezyum", "serum", "Biyokimya", "mg/dL", "numeric", ["Magnezyum", "Magnezyum (Mg)", "Mg"], None),
    ("serum.ck", "Kreatin Kinaz (CK)", "serum", "Biyokimya", "U/L", "numeric", ["CK", "Kreatin Kinaz", "CPK"], None),
    ("serum.amylase", "Amilaz", "serum", "Biyokimya", "U/L", "numeric", ["Amilaz"], None),
    ("serum.lipase", "Lipaz", "serum", "Biyokimya", "U/L", "numeric", ["Lipaz"], None),
    # ---------------- Lipid ----------------
    ("serum.chol_total", "Total Kolesterol", "serum", "Lipid", "mg/dL", "numeric", ["Total Kolesterol", "Kolesterol", "Kolesterol (Total)"], None),
    ("serum.hdl", "HDL Kolesterol", "serum", "Lipid", "mg/dL", "numeric", ["HDL Kolesterol", "HDL", "HDL-Kolesterol"], None),
    ("serum.ldl", "LDL Kolesterol", "serum", "Lipid", "mg/dL", "numeric", ["LDL Kolesterol", "LDL", "LDL-Kolesterol", "LDL Kolesterol (Hesaplanan)", "LDL (Direkt)"], None),
    ("serum.vldl", "VLDL Kolesterol", "serum", "Lipid", "mg/dL", "numeric", ["VLDL Kolesterol", "VLDL"], None),
    ("serum.triglyceride", "Trigliserid", "serum", "Lipid", "mg/dL", "numeric", ["Trigliserid", "Trigliserit", "TG"], None),
    ("serum.non_hdl", "Non-HDL Kolesterol", "serum", "Lipid", "mg/dL", "numeric", ["Non-HDL Kolesterol", "Non HDL Kolesterol"], None),
    # ---------------- Tiroid ----------------
    ("serum.tsh", "TSH", "serum", "Tiroid", "mIU/L", "numeric", ["TSH", "Tiroid Stimülan Hormon"], None),
    ("serum.ft4", "Serbest T4", "serum", "Tiroid", "ng/dL", "numeric", ["Serbest T4", "sT4", "FT4", "Serbest Tiroksin"], None),
    ("serum.ft3", "Serbest T3", "serum", "Tiroid", "pg/mL", "numeric", ["Serbest T3", "sT3", "FT3"], None),
    ("serum.anti_tpo", "Anti-TPO", "serum", "Tiroid", "IU/mL", "numeric", ["Anti-TPO", "Anti TPO", "Tiroid Peroksidaz Antikoru"], None),
    ("serum.anti_tg", "Anti-Tiroglobulin", "serum", "Tiroid", "IU/mL", "numeric", ["Anti-Tg", "Anti Tiroglobulin", "Anti-Tiroglobulin"], None),
    # ---------------- Vitamin ve mineral ----------------
    ("serum.b12", "Vitamin B12", "serum", "Vitamin ve Mineral", "ng/L", "numeric", ["Vitamin B12", "B12", "B12 Vitamini", "Kobalamin"], None),
    ("serum.vit_d", "25-OH Vitamin D", "serum", "Vitamin ve Mineral", "ng/mL", "numeric", ["25-OH Vitamin D", "Vitamin D", "25 (OH) Vitamin D", "25-Hidroksi Vitamin D", "D Vitamini"], None),
    ("serum.folate", "Folat", "serum", "Vitamin ve Mineral", "ng/mL", "numeric", ["Folat", "Folik Asit"], None),
    ("serum.ferritin", "Ferritin", "serum", "Vitamin ve Mineral", "µg/L", "numeric", ["Ferritin"], None),
    ("serum.iron", "Demir (Fe)", "serum", "Vitamin ve Mineral", "µg/dL", "numeric", ["Demir", "Demir (Fe)", "Serum Demiri", "Fe"], None),
    ("serum.tibc", "Total Demir Bağlama Kapasitesi", "serum", "Vitamin ve Mineral", "µg/dL", "numeric", ["TDBK", "Total Demir Bağlama Kapasitesi", "Demir Bağlama Kapasitesi Total", "Demir BK Total", "Total Demir BK", "TIBC"], None),
    ("serum.uibc", "Doymamış Demir Bağlama Kapasitesi", "serum", "Vitamin ve Mineral", "µg/dL", "numeric", ["UIBC", "Doymamış Demir Bağlama Kapasitesi", "Demir Bağlama Kapasitesi", "Demir BK", "Demir BK (UIBC)", "Doymamış Demir BK"], None),
    ("serum.zinc", "Çinko", "serum", "Vitamin ve Mineral", "µg/dL", "numeric", ["Çinko", "Zn"], None),
    # ---------------- Diyabet ----------------
    ("blood.hba1c", "HbA1c", "blood", "Diyabet", "%", "numeric", ["HbA1c", "Hemoglobin A1c", "Glikozile Hemoglobin", "HbA1C", "HbA1c (NGSP)", "HbA1c (IFCC)", "HbA1c NGSP"], None),
    ("serum.insulin", "İnsülin", "serum", "Diyabet", "µIU/mL", "numeric", ["İnsülin", "Insulin", "Açlık İnsülini"], None),
    # ---------------- İnflamasyon ----------------
    ("serum.crp", "C-Reaktif Protein (CRP)", "serum", "İnflamasyon", "mg/L", "numeric", ["CRP", "C-Reaktif Protein", "C Reaktif Protein", "C-Reaktif Protein (CRP)"], None),
    ("serum.hs_crp", "hs-CRP", "serum", "İnflamasyon", "mg/L", "numeric", ["hs-CRP", "hsCRP", "Yüksek Duyarlıklı CRP"], None),
    ("serum.procalcitonin", "Prokalsitonin", "serum", "İnflamasyon", "ng/mL", "numeric", ["Prokalsitonin"], None),
    # ---------------- Hormon ----------------
    ("serum.cortisol", "Kortizol", "serum", "Hormon", "µg/dL", "numeric", ["Kortizol"], None),
    ("serum.prolactin", "Prolaktin", "serum", "Hormon", "ng/mL", "numeric", ["Prolaktin"], None),
    ("serum.testosterone", "Total Testosteron", "serum", "Hormon", "ng/dL", "numeric", ["Testosteron", "Total Testosteron"], None),
    ("serum.estradiol", "Östradiol (E2)", "serum", "Hormon", "pg/mL", "numeric", ["Östradiol", "E2", "Östradiol (E2)"], None),
    ("serum.fsh", "FSH", "serum", "Hormon", "mIU/mL", "numeric", ["FSH"], None),
    ("serum.lh", "LH", "serum", "Hormon", "mIU/mL", "numeric", ["LH"], None),
    ("serum.psa_total", "Total PSA", "serum", "Hormon", "ng/mL", "numeric", ["Total PSA", "PSA", "PSA (Total)", "PSA Total", "tPSA"], None),
    ("serum.psa_free", "Serbest PSA", "serum", "Hormon", "ng/mL", "numeric", ["Serbest PSA", "PSA Serbest", "PSA (Serbest)", "fPSA", "Free PSA"], None),
    ("serum.psa_ratio", "Serbest/Total PSA Oranı", "serum", "Hormon", "%", "numeric", ["Serbest/Total PSA", "Serbest PSA/Total PSA", "fPSA/tPSA", "Serbest/Total PSA Oranı", "PSA Oranı"], None),
    # ---------------- Koagülasyon ----------------
    ("blood.pt", "Protrombin Zamanı (PT)", "blood", "Koagülasyon", "sn", "numeric", ["PT", "Protrombin Zamanı"], None),
    ("blood.inr", "INR", "blood", "Koagülasyon", None, "numeric", ["INR", "PT-INR"], None),
    ("blood.aptt", "aPTT", "blood", "Koagülasyon", "sn", "numeric", ["aPTT", "APTT"], None),
    ("blood.d_dimer", "D-Dimer", "blood", "Koagülasyon", "µg/mL", "numeric", ["D-Dimer", "D Dimer"], None),
    ("blood.fibrinogen", "Fibrinojen", "blood", "Koagülasyon", "mg/dL", "numeric", ["Fibrinojen"], None),
    # ---------------- İdrar ----------------
    ("urine.color", "Renk", "urine", "İdrar", None, "qualitative", ["Renk"], None),
    ("urine.clarity", "Görünüm", "urine", "İdrar", None, "qualitative", ["Görünüm", "Berraklık", "Bulanıklık"], None),
    ("urine.density", "Dansite", "urine", "İdrar", None, "numeric", ["Dansite", "Yoğunluk", "Özgül Ağırlık", "Dansite (Yoğunluk)"], DENSITY_RULE),
    ("urine.ph", "pH", "urine", "İdrar", None, "numeric", ["pH", "PH"], None),
    ("urine.protein", "Protein", "urine", "İdrar", None, "qualitative", ["Protein"], None),
    ("urine.glucose", "Glukoz", "urine", "İdrar", None, "qualitative", ["Glukoz", "Glikoz"], None),
    ("urine.ketone", "Keton", "urine", "İdrar", None, "qualitative", ["Keton", "Keton Cisimleri"], None),
    ("urine.bilirubin", "Bilirubin", "urine", "İdrar", None, "qualitative", ["Bilirubin"], None),
    ("urine.urobilinogen", "Ürobilinojen", "urine", "İdrar", None, "qualitative", ["Ürobilinojen", "Urobilinojen"], None),
    ("urine.nitrite", "Nitrit", "urine", "İdrar", None, "qualitative", ["Nitrit"], None),
    ("urine.blood", "Eritrosit (strip)", "urine", "İdrar", None, "qualitative", ["Eritrosit", "Kan", "Hemoglobin", "Eritrosit (hemoglobin)", "Eritrosit (Hb)"], None),
    ("urine.leukocyte_esterase", "Lökosit (strip)", "urine", "İdrar", None, "qualitative", ["Lökosit", "Lökosit Esteraz", "Lökosit (esteraz)"], None),
    ("urine.micro_rbc", "Eritrosit (mikroskopi)", "urine", "İdrar", "/HPF", "numeric", ["Eritrosit (Mikroskopi)", "Mikroskopi Eritrosit", "RBC/HPF", "Eritrosit (HPF)"], None),
    ("urine.micro_wbc", "Lökosit (mikroskopi)", "urine", "İdrar", "/HPF", "numeric", ["Lökosit (Mikroskopi)", "Mikroskopi Lökosit", "WBC/HPF", "Lökosit (HPF)"], None),
    ("urine.epithelium", "Epitel", "urine", "İdrar", "/HPF", "numeric", ["Epitel", "Epitel Hücresi", "Yassı Epitel"], None),
    ("urine.bacteria", "Bakteri", "urine", "İdrar", None, "qualitative", ["Bakteri"], None),
    ("urine.yeast", "Maya", "urine", "İdrar", None, "qualitative", ["Maya", "Maya Hücresi"], None),
    ("urine.crystal", "Kristal", "urine", "İdrar", None, "qualitative", ["Kristal", "Kristaller"], None),
    ("urine.cylinder", "Silindir", "urine", "İdrar", None, "qualitative", ["Silindir"], None),
    ("urine.mucus", "Mukus", "urine", "İdrar", None, "qualitative", ["Mukus"], None),
    ("urine.culture", "İdrar Kültürü", "urine", "İdrar", None, "text", ["İdrar Kültürü", "Kültür", "Bakteri İzole", "Üreme"], None),
    ("urine.microalbumin", "Mikroalbümin", "urine", "İdrar", "mg/L", "numeric", ["Mikroalbümin", "Mikroalbumin"], None),
    # ---------------- Seroloji ----------------
    ("serum.hbsag", "HBsAg", "serum", "Seroloji", None, "qualitative", ["HBsAg"], None),
    ("serum.anti_hbs", "Anti-HBs", "serum", "Seroloji", "mIU/mL", "qualitative", ["Anti-HBs", "Anti HBs"], None),
    ("serum.anti_hcv", "Anti-HCV", "serum", "Seroloji", None, "qualitative", ["Anti-HCV", "Anti HCV"], None),
    ("serum.anti_hiv", "Anti-HIV", "serum", "Seroloji", None, "qualitative", ["Anti-HIV", "Anti HIV", "HIV 1/2 Antikor"], None),
    ("serum.vdrl", "VDRL-RPR", "serum", "Seroloji", None, "qualitative", ["VDRL", "RPR", "VDRL-RPR"], None),
    ("serum.aso", "ASO", "serum", "Seroloji", "IU/mL", "numeric", ["ASO", "Anti Streptolizin O"], None),
    ("serum.rf", "Romatoid Faktör (RF)", "serum", "Seroloji", "IU/mL", "numeric", ["RF", "Romatoid Faktör"], None),
    ("blood.abo_rh", "Kan Grubu", "blood", "Seroloji", None, "text", ["Kan Grubu", "ABO Rh", "Kan Grubu (ABO/Rh)", "ABO-Rh"], None),
    # ---------------- Ölçümler (elle giriş) ----------------
    ("vital.weight", "Kilo", "other", "Ölçümler", "kg", "numeric", ["Kilo", "Ağırlık"], None),
    ("vital.bp_sys", "Tansiyon (büyük)", "other", "Ölçümler", "mmHg", "numeric", ["Sistolik", "Büyük Tansiyon", "Tansiyon (büyük)"], None),
    ("vital.bp_dia", "Tansiyon (küçük)", "other", "Ölçümler", "mmHg", "numeric", ["Diastolik", "Küçük Tansiyon", "Tansiyon (küçük)"], None),
    ("vital.pulse", "Nabız", "other", "Ölçümler", "atım/dk", "numeric", ["Nabız"], None),
    ("vital.glucose_home", "Evde Şeker Ölçümü", "other", "Ölçümler", "mg/dL", "numeric", ["Şeker", "Kan Şekeri", "Evde Şeker Ölçümü"], None),
    ("vital.temperature", "Ateş", "other", "Ölçümler", "°C", "numeric", ["Ateş", "Vücut Sıcaklığı"], None),
    ("vital.spo2", "Oksijen Satürasyonu", "other", "Ölçümler", "%", "numeric", ["SpO2", "Oksijen Satürasyonu"], None),
]

BUILTIN_NAMES: dict[str, str] = {c[0]: c[1] for c in CATALOG}

CATEGORY_ORDER = [
    "Hemogram", "Biyokimya", "Lipid", "Tiroid", "Vitamin ve Mineral", "Diyabet", "İnflamasyon",
    "Hormon", "Koagülasyon", "İdrar", "Seroloji", "Ölçümler",
]


def seed_catalog(db: Session) -> int:
    existing = {t.key: t for t in db.scalars(select(TestDefinition))}
    existing_aliases = {(a.alias_normalized, a.specimen) for a in db.scalars(select(TestAlias))}
    added = 0
    for order, (key, name, specimen, cat, unit, vtype, aliases, rules) in enumerate(CATALOG):
        td = existing.get(key)
        if td is None:
            td = TestDefinition(
                key=key, display_name=name, specimen=specimen, category=cat, canonical_unit=unit,
                value_type=vtype, unit_rules=rules, sort_order=order, is_builtin=True,
            )
            db.add(td)
            db.flush()
            added += 1
        # Açıklamalar: yalnızca hiç girilmemiş (NULL) alanlar doldurulur; kullanıcının
        # düzenlediği (boş bırakılmış dahil) metinlere dokunulmaz.
        info = CATALOG_INFO.get(key)
        if info:
            for field, text in zip(("info_what", "info_low", "info_high"), info):
                if text is not None and getattr(td, field) is None:
                    setattr(td, field, text)
        for a in [name, *aliases]:
            k = (normalize_alias(a), specimen)
            if k in existing_aliases:
                continue
            db.add(TestAlias(test_definition_id=td.id, alias_normalized=k[0], specimen=specimen))
            existing_aliases.add(k)
    db.commit()
    return added
