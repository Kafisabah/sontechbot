import json
import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class IssueRepository(BaseRepository):

    def add_sync_issue(self, erp_product_id, barcode, erp_branch_name,
                       issue_type, message, details_dict=None):
        check_sql = """
            SELECT id FROM sync_issues
            WHERE erp_product_id = ? AND erp_branch_name = ?
            AND issue_type = ? AND is_resolved = 0
        """
        product_id = str(erp_product_id or '')
        branch_name = str(erp_branch_name or '')

        existing = self._execute(check_sql, (product_id, branch_name, issue_type), fetch='one')
        if existing:
            return None

        details_json_str = json.dumps(details_dict, ensure_ascii=False) if details_dict else None
        insert_sql = """
            INSERT INTO sync_issues (
                erp_product_id, barcode, erp_branch_name,
                issue_type, message, details_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            product_id, str(barcode or ''), branch_name,
            str(issue_type), str(message), details_json_str
        )
        return self._execute(insert_sql, params, commit=True)

    def get_all_unresolved_issues(self):
        query = "SELECT * FROM sync_issues WHERE is_resolved = 0 ORDER BY timestamp DESC"
        rows = self._execute(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def get_all_resolved_issues(self):
        query = "SELECT * FROM sync_issues WHERE is_resolved = 1 ORDER BY timestamp DESC"
        rows = self._execute(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def get_all_issues(self):
        query = "SELECT * FROM sync_issues ORDER BY timestamp DESC"
        rows = self._execute(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def mark_issue_resolved(self, issue_id):
        query = "UPDATE sync_issues SET is_resolved = 1 WHERE id = ?"
        return self._execute(query, (issue_id,), commit=True) is not None