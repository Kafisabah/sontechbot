import json
import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class HistoryRepository(BaseRepository):

    def add_sync_history_entry(self, summary_data):
        sql = """
            INSERT INTO sync_history (
                start_time, duration_seconds, sync_type, status,
                products_processed, products_sent, issues_found,
                summary_message, batch_request_id, batch_status_details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            summary_data.get('start_time'),
            summary_data.get('duration_seconds'),
            summary_data.get('sync_type'),
            summary_data.get('status'),
            summary_data.get('products_processed'),
            summary_data.get('products_sent'),
            summary_data.get('issues_found'),
            summary_data.get('summary_message'),
            summary_data.get('batch_request_id'),
            json.dumps(summary_data.get('batch_status_details', {}), ensure_ascii=False)
        )
        return self._execute(sql, params, commit=True)

    def get_sync_history(self, limit=50):
        query = "SELECT * FROM sync_history ORDER BY start_time DESC LIMIT ?"
        rows = self._execute(query, (limit,), fetch='all')
        return [dict(row) for row in rows] if rows else []