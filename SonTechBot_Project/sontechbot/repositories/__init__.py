# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 09:15
# Yapılan Değişiklikler:
# 1. Kullanıcının isteği üzerine, 'brand_mappings' tablosu ve 'brand_repo' referansı kaldırıldı.
# 2. 'branch_mappings' tablosundaki 'trendyol_store_id' sütunu korundu.
# 3. Kategori kuralları tablosu ('category_rules') korundu.

import logging

from .base_repository import BaseRepository
from .branch_repository import BranchRepository
from .category_repository import CategoryRepository
from .dashboard_repository import DashboardRepository
from .history_repository import HistoryRepository
from .issue_repository import IssueRepository
from .product_repository import ProductRepository
from .settings_repository import SettingsRepository
# from .brand_repository import BrandRepository # Marka repository artık kullanılmıyor

logger = logging.getLogger(__name__)

# Tüm repository sınıflarından birer örnek oluşturuluyor
issue_repo = IssueRepository()
settings_repo = SettingsRepository()
branch_repo = BranchRepository()
category_repo = CategoryRepository()
# brand_repo = BrandRepository() # Marka repository artık kullanılmıyor
product_repo = ProductRepository()
history_repo = HistoryRepository()
dashboard_repo = DashboardRepository()


def initialize_database():
    """
    Uygulamanın ihtiyaç duyduğu tüm veritabanı tablolarını oluşturur.
    """
    logger.info("Veritabanı tabloları başlatılıyor...")
    base = BaseRepository()

    # Tüm tabloları oluşturan ana SQL betiği
    create_script = """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, erp_product_id TEXT UNIQUE NOT NULL, stok_kod TEXT, name TEXT NOT NULL, barcode1 TEXT,
        barcode2 TEXT, unit TEXT, vat_rate INTEGER, erp_grup_kod TEXT, erp_marka_adi TEXT, web_publish_flag INTEGER DEFAULT 1,
        description TEXT, last_updated_from_erp DATETIME, created_at DATETIME
    );
    CREATE TABLE IF NOT EXISTS branch_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        erp_branch_name TEXT NOT NULL, 
        erp_location_id TEXT NOT NULL UNIQUE, 
        erp_price_list_id TEXT NOT NULL,
        trendyol_store_id TEXT, -- Şube bazlı güncelleme için Mağaza ID'si
        stock_buffer INTEGER DEFAULT 0, 
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS category_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        erp_category_id TEXT NOT NULL UNIQUE, 
        erp_category_name TEXT,
        sync_enabled INTEGER DEFAULT 1, 
        price_adjustment_percentage REAL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS sync_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, erp_product_id TEXT, barcode TEXT, erp_branch_name TEXT,
        issue_type TEXT, message TEXT, details_json TEXT, is_resolved INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, start_time DATETIME NOT NULL, duration_seconds REAL, sync_type TEXT, status TEXT,
        products_processed INTEGER, products_sent INTEGER, issues_found INTEGER, summary_message TEXT, batch_request_id TEXT,
        batch_status_details_json TEXT
    );
    CREATE TABLE IF NOT EXISTS product_platform_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, erp_product_id TEXT NOT NULL, erp_barcode TEXT, platform_name TEXT NOT NULL,
        platform_content_id TEXT, platform_product_id TEXT, last_sync_date DATETIME, last_sync_status TEXT,
        UNIQUE (platform_name, erp_product_id), UNIQUE (platform_name, erp_barcode)
    );
    """
    base._execute(create_script, script=True, commit=True)
    logger.info("Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu.")


def close_database_connection():
    """Uygulama kapatılırken veritabanı bağlantısını güvenli bir şekilde sonlandırır."""
    base = BaseRepository()
    if getattr(base, '_conn', None):
        base._conn.close()
        base._conn = None
        logger.info("Merkezi veritabanı bağlantısı kapatıldı.")
