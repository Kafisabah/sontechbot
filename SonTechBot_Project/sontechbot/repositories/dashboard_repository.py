import datetime
import logging

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class DashboardRepository(BaseRepository):

    def get_dashboard_stats(self):
        stats = {
            "health_score": 100,
            "issue_counts": {},
            "last_sync_duration": "N/A",
            "last_sync_summary": "Henüz senkronizasyon yapılmadı.",
            "total_unresolved_issues": 0
        }

        if not self._get_connection():
            stats["last_sync_summary"] = "Veritabanı bağlantısı yok."
            return stats

        try:
            twenty_four_hours_ago = (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            history_query = "SELECT status FROM sync_history WHERE start_time >= ?"
            history_rows = self._execute(history_query, (twenty_four_hours_ago,), fetch='all')
            if history_rows:
                total_syncs = len(history_rows)
                successful_syncs = sum(1 for row in history_rows if row['status'] in ['Başarılı', 'Uyarılarla Tamamlandı'])
                stats['health_score'] = round((successful_syncs / total_syncs * 100) if total_syncs > 0 else 100)

            issue_query = "SELECT issue_type, COUNT(*) as count FROM sync_issues WHERE is_resolved = 0 GROUP BY issue_type"
            issue_rows = self._execute(issue_query, fetch='all')
            if issue_rows:
                stats['issue_counts'] = {row['issue_type']: row['count'] for row in issue_rows}

            total_issues_query = "SELECT COUNT(*) as count FROM sync_issues WHERE is_resolved = 0"
            total_issues_row = self._execute(total_issues_query, fetch='one')
            if total_issues_row:
                stats['total_unresolved_issues'] = total_issues_row['count']

            last_sync_query = "SELECT duration_seconds, summary_message FROM sync_history ORDER BY start_time DESC LIMIT 1"
            last_sync_row = self._execute(last_sync_query, fetch='one')
            if last_sync_row:
                stats['last_sync_duration'] = f"{last_sync_row['duration_seconds']:.2f} saniye"
                stats['last_sync_summary'] = last_sync_row['summary_message']

        except Exception as e:
            logger.error(f"Dashboard istatistikleri okunurken bir hata oluştu: {e}", exc_info=True)

        return stats