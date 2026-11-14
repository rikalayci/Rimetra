"""Örnek e-Nabız raporları (RIMETRA.md'deki gözlemlerden türetilmiş)."""


def family_practice_report(member_id: str) -> dict:
    """Aile hekimliği raporu: hemogram + idrar + adsız biyokimya paneli."""
    t = "2025-03-12T09:12:00+03:00"
    return {
        "member_id": member_id,
        "source": "enabiz",
        "report_date": "2025-03-12",
        "facility": "ÖRNEK 12 NOLU AİLE HEKİMLİĞİ BİRİMİ",
        "patient_name_on_document": "BURAK YILMAZ",
        "panels": [
            {
                "name": "Tam Kan Sayımı (Hemogram)",
                "sample_datetime": t,
                "specimen": "blood",
                "results": [
                    {"raw_name": "Lökosit (WBC)", "raw_value": "3.9", "raw_unit": "10³/µL", "raw_reference": "4.4 - 11.3", "source_flag": "alert"},
                    {"raw_name": "Hemoglobin (Hb)", "raw_value": "15.1", "raw_unit": "g/dL", "raw_reference": "13.5 - 17", "source_flag": "ok"},
                    {"raw_name": "# Lenfosit # Lenfosit", "raw_value": "2,1", "raw_unit": "10³/µL", "raw_reference": "1 - 3.2", "source_flag": "ok"},
                    {"raw_name": "MCH", "raw_value": "27.4", "raw_unit": "pg", "raw_reference": "28 - 33", "source_flag": "alert"},
                ],
            },
            {
                "name": "İdrar tetkiki ve mikroskopisi",
                "sample_datetime": t,
                "specimen": "urine",
                "results": [
                    {"raw_name": "Protein", "raw_value": "Pozitif (++)", "raw_reference": "NEGATİF", "source_flag": "alert"},
                    {"raw_name": "Dansite", "raw_value": "1.012", "raw_reference": "1.005 - 1.025", "source_flag": "ok"},
                    {"raw_name": "Eritrosit.", "raw_value": "POZİTİF (++++)", "raw_reference": "NEGATİF -", "source_flag": "ok"},
                    {"raw_name": "Keton", "raw_value": "ESER", "raw_reference": "- Referans Açıklama : NEGATİF", "source_flag": "ok"},
                    {"raw_name": "Lökosit", "raw_value": "Negatif", "raw_reference": "NEGATİF", "source_flag": "ok"},
                    {"raw_name": "Bakteri Bakteri", "raw_value": "Negatif", "raw_reference": "NEGATİF", "source_flag": "ok"},
                    {"raw_name": "Glukoz", "raw_value": "Negatif", "raw_reference": "NEGATİF", "source_flag": "ok"},
                    {"raw_name": "Silindir", "raw_value": ".", "raw_reference": "", "source_flag": None},
                ],
            },
            {
                "name": None,
                "sample_datetime": t,
                "specimen": "serum",
                "results": [
                    {"raw_name": "ALT", "raw_value": "19", "raw_unit": "U/L", "raw_reference": "&lt;41", "source_flag": "ok"},
                    {"raw_name": "Glukoz", "raw_value": "86", "raw_unit": "mg/dL",
                     "raw_reference": "74 - 106 - Diyabet : ?126 Tokluk Kan Glukozu: &lt;140 Hipoglisemi : &lt;70", "source_flag": "ok"},
                    {"raw_name": "Ürik Asit", "raw_value": "8.6", "raw_unit": "mg/dL", "raw_reference": "3.4 - 7", "source_flag": "alert"},
                    {"raw_name": "CRP", "raw_value": "24,6", "raw_unit": "mg/L", "raw_reference": "0 - 5", "source_flag": "alert"},
                ],
            },
        ],
    }


def private_hospital_report(member_id: str) -> dict:
    """Özel hastane: idrar + kültür (sayfa bölünmesi ajan tarafından birleştirilmiş)."""
    t = "2025-03-13T10:40:00+03:00"
    return {
        "member_id": member_id,
        "source": "enabiz",
        "report_date": "2025-03-13",
        "facility": "Örnek Özel Hastane",
        "patient_name_on_document": "BURAK YILMAZ",
        "panels": [
            {
                "name": "Tam İdrar Analizi",
                "sample_datetime": t,
                "specimen": "urine",
                "results": [
                    {"raw_name": "Dansite", "raw_value": "1005", "raw_reference": "1005 - 1030", "source_flag": "ok"},
                    {"raw_name": "pH", "raw_value": "6", "raw_reference": "5 - 8", "source_flag": "ok"},
                ],
            },
            {
                "name": "İdrar Kültürü",
                "sample_datetime": t,
                "specimen": "urine",
                "results": [
                    {"raw_name": "Kültür", "raw_value": "Bakteri izole edilmedi.", "raw_reference": "", "source_flag": None},
                ],
            },
        ],
    }
