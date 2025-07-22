# sontechbot/ui/popups/__init__.py
# Son Güncelleme: 9 Haziran 2025, 23:30 (TR Saati)
# - YAPI DÜZELTME: Artık kullanılmayan popup referansları kaldırıldı.
# - Bu dosya artık sadece gerçekten popup olarak kullanılan sınıfları dışa aktarır.

from .auto_sync_status_popup import AutoSyncStatusPopup
from .error_reports_popup import ErrorDetailPopup 
# Not: ErrorReportsPopup kaldırıldı, sadece ErrorDetailPopup kaldı.

# Dışarıya açılacak sınıflar güncellendi
__all__ = [
    'AutoSyncStatusPopup',
    'ErrorDetailPopup',
]