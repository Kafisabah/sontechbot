import datetime
import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository):

    def add_or_update_product_mapping(self, erp_product_id, erp_barcode,
                                      platform_name, platform_content_id):
        sql = """
            INSERT INTO product_platform_mappings (
                erp_product_id, erp_barcode, platform_name,
                platform_content_id, last_sync_date, last_sync_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform_name, erp_product_id) DO UPDATE SET
                erp_barcode=excluded.erp_barcode,
                platform_content_id=excluded.platform_content_id,
                last_sync_date=excluded.last_sync_date,
                last_sync_status=excluded.last_sync_status
        """
        params = (
            str(erp_product_id),
            str(erp_barcode),
            platform_name,
            str(platform_content_id),
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'SUCCESS'
        )
        return self._execute(sql, params, commit=True)

    def get_product_mapping_by_barcode(self, barcode, platform_name):
        query = "SELECT * FROM product_platform_mappings WHERE erp_barcode = ? AND platform_name = ?"
        row = self._execute(query, (str(barcode), platform_name), fetch='one')
        return dict(row) if row else None