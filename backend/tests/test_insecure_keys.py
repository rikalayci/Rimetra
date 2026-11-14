"""Varsayılan / örnek anahtarlarla uygulama açılmamalı."""
import pytest

from app import main
from app.config import Settings


def test_example_keys_are_rejected(monkeypatch):
    s = Settings(secret_key="degistir-bunu-uzun-rastgele-bir-deger-yap", data_encryption_key="dev-data-key-change-me")
    assert s.insecure_keys() == ["SECRET_KEY", "DATA_ENCRYPTION_KEY"]
    monkeypatch.setattr(main, "get_settings", lambda: s)
    with pytest.raises(RuntimeError):
        main._check_keys()


def test_override_and_real_keys_pass(monkeypatch):
    s = Settings(secret_key="dev-secret-change-me", data_encryption_key="x" * 40, allow_insecure_keys=True)
    monkeypatch.setattr(main, "get_settings", lambda: s)
    main._check_keys()  # uyarı verir, hata vermez
    assert Settings(secret_key="a" * 40, data_encryption_key="b" * 40).insecure_keys() == []
