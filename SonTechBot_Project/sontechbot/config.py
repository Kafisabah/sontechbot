# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 07.07.2025 04:30
# Yapılan Değişiklikler:
# 1. Artık otomatik olarak algılandığı için, ERP_DATABASE_CONFIG_DEFAULT içerisindeki "driver" anahtarı kaldırıldı.

import os
from appdirs import user_data_dir

# --- Uygulama Kimlik Bilgileri ---
APP_NAME = "SonTechBot"
APP_AUTHOR = "SonTech"

# --- Kalıcı Veri Yolları ---
USER_DATA_DIR = user_data_dir(APP_NAME, APP_AUTHOR)
LOGS_DIR = os.path.join(USER_DATA_DIR, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "sontechbot_app.log")
_DATABASE_FILE_PATH = os.path.join(USER_DATA_DIR, "sontechbot.db")

# --- Uygulama Bilgileri ---
APP_VERSION = "1.7.0"
APP_TITLE = "SonTechBot Entegrasyon Aracı"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# --- Varsayılan Yapılandırma Ayarları ---
ERP_DATABASE_CONFIG_DEFAULT = {
    "server": r"SERVER_NAME",
    "database": "DATABASE_NAME",
    "username": "USERNAME",
    "password": "PASSWORD"
}

TRENDYOL_API_CONFIG_DEFAULT = {
    "api_key": "TRNDYOL_API_KEY",
    "api_secret": "TRNDYOL_API_SECRET",
    "supplier_id": "TRNDYOL_SATICI_ID",
    "base_url": "https://api.tgoapps.com",
    "test_mode_enabled": True
}

GENERAL_SETTINGS_DEFAULT = {
    "sync_interval_minutes": 30,
    "database_file_path": _DATABASE_FILE_PATH,
    "log_level": "INFO"
}

# --- Lisanslama ve Güncelleme Ayarları ---
LICENSE_SERVER_URL = "https://www.41den.com/api/lisans_kontrol.php"
LICENSE_FILE = os.path.join(USER_DATA_DIR, "license.dat")
UPDATE_INFO_URL = "https://www.41den.com/updates/version.json"
