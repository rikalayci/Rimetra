from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Kodda ve .env.example'da duran örnek değerler. Bunlarla üretimde çalışmak güvensizdir.
INSECURE_KEY_VALUES = (
    "dev-secret-change-me",
    "dev-data-key-change-me",
    "degistir-bunu-uzun-rastgele-bir-deger-yap",
    "degistir-bunu-da-uzun-rastgele-bir-deger-yap",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rimetra:rimetra@localhost:5432/rimetra"
    data_path: Path = Path("./data")
    secret_key: str = "dev-secret-change-me"
    data_encryption_key: str = "dev-data-key-change-me"
    cookie_secure: bool = False
    session_hours: int = 168
    api_rate_limit_per_minute: int = 60
    login_fails_before_delay: int = 3
    max_pdf_mb: int = 25
    report_restore_days: int = 30
    public_base_url: str = "http://localhost:8080"
    tz: str = "Europe/Istanbul"

    initial_master_username: str = ""
    initial_master_password: str = ""
    initial_master_display_name: str = ""

    backup_enabled: bool = True
    backup_hour: int = 3
    backup_retention_days: int = 30

    # Telegram botu (boşsa bot kapalı)
    telegram_bot_token: str = ""
    # Yeni rapor eklenince bağlı kullanıcılara Telegram bildirimi gönderilsin mi (genel anahtar)
    telegram_notify: bool = True

    # testlerde arka plan işlerini kapatmak için
    disable_scheduler: bool = False

    # Yalnızca yerel geliştirme için: varsayılan/örnek anahtarlarla açılmaya izin ver
    allow_insecure_keys: bool = False

    def insecure_keys(self) -> list[str]:
        """Varsayılan veya .env.example'daki örnek değerde kalan anahtarların adları."""
        bad = {s.lower() for s in INSECURE_KEY_VALUES}
        out = []
        for name in ("secret_key", "data_encryption_key"):
            v = getattr(self, name).strip()
            if not v or v.lower() in bad:
                out.append(name.upper())
        return out

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    @property
    def pdf_dir(self) -> Path:
        return self.data_path / "pdfs"

    @property
    def avatar_dir(self) -> Path:
        return self.data_path / "avatars"

    @property
    def backup_dir(self) -> Path:
        return self.data_path / "backups"


@lru_cache
def get_settings() -> Settings:
    return Settings()
