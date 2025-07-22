# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 07.07.2025 09:10
# Yapılan Değişiklikler:
# 1. 'KeyError: 'driver'' hatasını çözmek için 'get_erp_config' fonksiyonu güncellendi.
# 2. Fonksiyon artık config dosyasında veya veritabanında 'driver' anahtarını aramıyor.

import logging

from .. import config
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SettingsRepository(BaseRepository):

    def get_app_setting(self, key, default=None):
        query = "SELECT value FROM app_settings WHERE key = ?"
        row = self._execute(query, (key,), fetch='one')
        value = row['value'] if row else default
        return value if value is not None else default

    def save_app_setting(self, key, value):
        query = "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)"
        return self._execute(query, (key, str(value)), commit=True)

    def get_erp_config(self):
        """
        ERP yapılandırmasını okur. Artık 'driver' anahtarını aramaz.
        """
        cfg = config.ERP_DATABASE_CONFIG_DEFAULT.copy()
        cfg["server"] = self.get_app_setting("erp_server", cfg.get("server"))
        cfg["database"] = self.get_app_setting("erp_database", cfg.get("database"))
        cfg["username"] = self.get_app_setting("erp_username", cfg.get("username"))
        cfg["password"] = self.get_app_setting("erp_password", cfg.get("password"))
        return cfg

    def get_trendyol_config(self):
        cfg = config.TRENDYOL_API_CONFIG_DEFAULT.copy()
        cfg["api_key"] = self.get_app_setting("trendyol_api_key", cfg.get("api_key"))
        cfg["api_secret"] = self.get_app_setting("trendyol_api_secret", cfg.get("api_secret"))
        cfg["supplier_id"] = self.get_app_setting("trendyol_supplier_id", cfg.get("supplier_id"))

        test_mode_str = self.get_app_setting("trendyol_test_mode_enabled", "True")
        cfg["test_mode_enabled"] = (test_mode_str == 'True')
        return cfg

    def get_general_settings(self):
        cfg = config.GENERAL_SETTINGS_DEFAULT.copy()
        sync_interval = self.get_app_setting("sync_interval_minutes", cfg.get("sync_interval_minutes"))
        cfg["sync_interval_minutes"] = int(sync_interval or 15)
        cfg["log_level"] = self.get_app_setting("log_level", cfg.get("log_level"))
        return cfg
