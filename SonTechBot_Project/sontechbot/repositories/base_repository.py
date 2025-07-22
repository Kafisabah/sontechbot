# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 10:10
# Yapılan Değişiklikler:
# 1. Veritabanı dosyası bulunamadı hatasını çözmek için __init__ metoduna _ensure_db_folder fonksiyonu eklendi.
# 2. Bu fonksiyon, veritabanı dosyasının kaydedileceği klasörün (örn: C:\Users\kullanici\AppData\Local\SonTech\SonTechBot) var olup olmadığını kontrol eder ve yoksa oluşturur.

import logging
import os
import sqlite3

from ..config import GENERAL_SETTINGS_DEFAULT

logger = logging.getLogger(__name__)


class BaseRepository:
    _conn = None
    db_path = GENERAL_SETTINGS_DEFAULT.get("database_file_path")

    def __init__(self):
        """
        Sınıf başlatıldığında, veritabanı klasörünün mevcut olduğundan emin olur.
        """
        self._ensure_db_folder()

    def _ensure_db_folder(self):
        """
        Veritabanı dosyasının kaydedileceği klasörün varlığını kontrol eder,
        eğer klasör yoksa oluşturur.
        """
        db_folder = os.path.dirname(self.db_path)
        if db_folder and not os.path.exists(db_folder):
            try:
                os.makedirs(db_folder)
                logger.info(f"Veritabanı klasörü oluşturuldu: {db_folder}")
            except OSError as e:
                logger.error(f"Veritabanı klasörü oluşturulamadı: {e}", exc_info=True)

    def _get_connection(self):
        if BaseRepository._conn is None:
            try:
                BaseRepository._conn = sqlite3.connect(
                    self.db_path, timeout=10, check_same_thread=False
                )
                BaseRepository._conn.row_factory = sqlite3.Row
                BaseRepository._conn.execute("PRAGMA foreign_keys = ON;")
                logger.info(f"Yeni veritabanı bağlantısı oluşturuldu: {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Veritabanı bağlantısı oluşturulamadı: {e}", exc_info=True)
                return None
        return BaseRepository._conn

    def _execute(self, query, params=(), fetch=None, commit=False, script=False):
        conn = self._get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            if script:
                cursor.executescript(query)
            else:
                cursor.execute(query, params)

            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            else:
                result = cursor.lastrowid

            if commit:
                conn.commit()

            return result
        except sqlite3.Error as e:
            query_preview = query.splitlines()[0] if query else "EMPTY_QUERY"
            logger.error(f"Sorgu hatası: {query_preview}... - Hata: {e}")
            if commit:
                conn.rollback()
            return None
