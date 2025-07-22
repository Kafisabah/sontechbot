# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 05:10
# Yapılan Değişiklikler:
# 1. Marka eşleştirmelerini yönetmek için yeni bir repository sınıfı oluşturuldu.
# 2. Bu sınıf, 'brand_mappings' tablosu üzerinde okuma ve yazma işlemleri yapar.

import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BrandRepository(BaseRepository):
    """
    Marka eşleştirmeleri (ERP markası -> Trendyol markası) ile ilgili
    veritabanı işlemlerini yöneten sınıf.
    """

    def get_all_brand_mappings(self):
        """Veritabanındaki tüm marka eşleştirmelerini çeker."""
        query = "SELECT * FROM brand_mappings ORDER BY erp_brand_name"
        rows = self._execute(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def add_or_update_brand_mapping(self, mapping_data):
        """
        Yeni bir marka eşleştirmesi ekler veya mevcut olanı günceller.
        'ON CONFLICT' ifadesi sayesinde, aynı ERP markası için tekrar kayıt oluşturmak yerine
        mevcut kaydı günceller.
        """
        sql = """
            INSERT INTO brand_mappings (
                erp_brand_name, trendyol_brand_id, trendyol_brand_name
            )
            VALUES (?, ?, ?)
            ON CONFLICT(erp_brand_name) DO UPDATE SET
                trendyol_brand_id=excluded.trendyol_brand_id,
                trendyol_brand_name=excluded.trendyol_brand_name
        """
        params = (
            str(mapping_data["erp_brand_name"]),
            mapping_data.get("trendyol_brand_id"),
            str(mapping_data.get("trendyol_brand_name"))
        )
        return self._execute(sql, params, commit=True)
