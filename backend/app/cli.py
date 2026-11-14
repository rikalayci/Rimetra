"""Komut satırı: `rimetra <komut>`  (container içinde: docker compose exec app rimetra <komut>)"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


def _ask_password() -> str:
    while True:
        p1 = getpass.getpass("Şifre (en az 8 karakter): ")
        if len(p1) < 8:
            print("Şifre en az 8 karakter olmalı.")
            continue
        p2 = getpass.getpass("Şifre (tekrar): ")
        if p1 != p2:
            print("Şifreler uyuşmuyor.")
            continue
        return p1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rimetra", description="Rimetra yönetim komutları")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cm = sub.add_parser("create-master", help="Master kullanıcı oluşturur")
    cm.add_argument("--username")
    cm.add_argument("--password", help="Verilmezse sorulur")
    cm.add_argument("--display-name", help="Aile panelinde görünecek profil adı (ör. Burak)")

    rp = sub.add_parser("reset-password", help="Bir kullanıcının şifresini sıfırlar")
    rp.add_argument("username")

    sub.add_parser("seed-catalog", help="Yerleşik test kataloğunu günceller")
    sub.add_parser("backup", help="Şimdi şifreli yedek alır")

    rs = sub.add_parser("restore", help="Şifreli yedekten geri yükler (MEVCUT VERİNİN ÜZERİNE YAZAR)")
    rs.add_argument("file", help="Yedek dosyası (ör. /data/backups/rimetra-20250101-030000.tar.enc)")
    rs.add_argument("--yes", action="store_true", help="Onay sorma")

    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from .bootstrap import create_master, ensure_dirs
    from .catalog_seed import seed_catalog
    from .db import SessionLocal
    from .models import User, UserSession
    from .security import hash_password

    ensure_dirs()
    if args.cmd == "create-master":
        username = args.username or input("Kullanıcı adı: ").strip()
        display = args.display_name if args.display_name is not None else input("Profil adı (boş bırakılabilir): ").strip()
        password = args.password or _ask_password()
        with SessionLocal() as db:
            try:
                u = create_master(db, username, password, display or None)
            except ValueError as e:
                print(f"Hata: {e}")
                return 1
        print(f"Master kullanıcı oluşturuldu: {u.username}")
        return 0

    if args.cmd == "reset-password":
        with SessionLocal() as db:
            u = db.scalar(select(User).where(func.lower(User.username) == args.username.lower()))
            if not u:
                print("Kullanıcı bulunamadı.")
                return 1
            u.password_hash = hash_password(_ask_password())
            db.query(UserSession).filter(UserSession.user_id == u.id).delete()
            db.commit()
        print("Şifre güncellendi.")
        return 0

    if args.cmd == "seed-catalog":
        with SessionLocal() as db:
            print(f"{seed_catalog(db)} yeni test eklendi.")
        return 0

    if args.cmd == "backup":
        from .services.backup import run_backup
        info = run_backup()
        print(f"Yedek alındı: {info['name']} ({info['size']} bayt)")
        return 0

    if args.cmd == "restore":
        from .services.backup import restore_backup
        f = Path(args.file)
        if not f.exists():
            print("Dosya bulunamadı.")
            return 1
        if not args.yes:
            ok = input("Mevcut veritabanı ve dosyalar yedekteki haliyle DEĞİŞTİRİLECEK. Devam? (evet/hayır): ")
            if ok.strip().lower() != "evet":
                print("İptal edildi.")
                return 1
        restore_backup(f)
        print("Geri yükleme tamamlandı. Uygulamayı yeniden başlatın: docker compose restart app")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
