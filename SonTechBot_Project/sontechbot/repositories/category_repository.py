# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 09:25
# Yapılan Değişiklikler:
# 1. 'AttributeError' hatasını çözmek için fonksiyon adları '..._rules' olarak geri düzeltildi.
# 2. SQL sorguları, 'category_rules' tablosuyla çalışacak şekilde güncellendi.
# 3. Kod, marka/kategori eşleştirmesi olmadan, sadece kategori bazlı kuralları (aktif/pasif, fiyat artışı) yönetecek şekilde sadeleştirildi.

import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class CategoryRepository(BaseRepository):
    """
    Kategori bazlı kurallar (senkronizasyon durumu, fiyat artışı) ile ilgili
    veritabanı işlemlerini yöneten sınıf.
    """

    def get_all_category_rules(self):
        """Veritabanındaki tüm kategori kurallarını çeker."""
        query = "SELECT * FROM category_rules ORDER BY erp_category_name"
        rows = self._execute(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def add_or_update_category_rule(self, rule_data):
        """
        Yeni bir kategori kuralı ekler veya mevcut olanı günceller.
        """
        sql = """
            INSERT INTO category_rules (
                erp_category_id, erp_category_name, sync_enabled,
                price_adjustment_percentage
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(erp_category_id) DO UPDATE SET
                erp_category_name=excluded.erp_category_name,
                sync_enabled=excluded.sync_enabled,
                price_adjustment_percentage=excluded.price_adjustment_percentage
        """
        params = (
            str(rule_data["erp_category_id"]),
            str(rule_data.get("erp_category_name")),
            1 if rule_data.get("sync_enabled") else 0,
            float(rule_data.get("price_adjustment_percentage", 0.0))
        )
        return self._execute(sql, params, commit=True)
