# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 05:20
# Yapılan Değişiklikler:
# 1. 'add_or_update_branch_mapping' fonksiyonu, artık 'trendyol_store_id' alanını da kaydedecek şekilde güncellendi.
# 2. SQL sorguları ve parametreler, yeni veritabanı şemasıyla uyumlu hale getirildi.

import json
import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BranchRepository(BaseRepository):
    """
    Şube eşleştirmeleri (ERP lokasyonu -> Trendyol Mağazası) ile ilgili
    veritabanı işlemlerini yöneten sınıf.
    """

    def get_all_branch_mappings(self):
        """Veritabanındaki tüm şube eşleştirmelerini çeker."""
        query = "SELECT * FROM branch_mappings ORDER BY erp_branch_name"
        rows = self._execute(query, fetch='all')
        if not rows:
            return []

        mappings = []
        for row in rows:
            mapping_dict = dict(row)
            try:
                # JSON verilerini Python listelerine dönüştür
                mapping_dict['categories_to_sync'] = json.loads(row['categories_to_sync_json'] or '[]')
                mapping_dict['excluded_categories'] = json.loads(row['excluded_categories_json'] or '[]')
                mapping_dict['is_active_for_sync'] = bool(row['is_active'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"ID'si {row['id']} olan şube için JSON verisi bozuk, varsayılanlar kullanılıyor.")
                mapping_dict['categories_to_sync'] = []
                mapping_dict['excluded_categories'] = []
                mapping_dict['is_active_for_sync'] = True
            mappings.append(mapping_dict)
        return mappings

    def add_or_update_branch_mapping(self, branch_data):
        """
        Yeni bir şube eşleştirmesi ekler veya mevcut olanı günceller.
        """
        sql = """
            INSERT INTO branch_mappings (
                erp_branch_name, erp_location_id, erp_price_list_id,
                stock_buffer, trendyol_store_id, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(erp_location_id) DO UPDATE SET
                erp_branch_name=excluded.erp_branch_name,
                erp_price_list_id=excluded.erp_price_list_id,
                stock_buffer=excluded.stock_buffer,
                trendyol_store_id=excluded.trendyol_store_id,
                is_active=excluded.is_active
        """
        params = (
            str(branch_data.get("erp_branch_name")),
            str(branch_data["erp_location_id"]),
            str(branch_data.get("erp_price_list_id", "0")),
            int(branch_data.get("stock_buffer", 0)),
            str(branch_data.get("trendyol_store_id")), # YENİ
            1 if branch_data.get("is_active") else 0,
        )
        return self._execute(sql, params, commit=True)
