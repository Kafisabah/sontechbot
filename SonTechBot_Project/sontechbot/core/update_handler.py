# sontechbot/core/update_handler.py

import logging
import requests
from packaging.version import parse as parse_version

from ..config import APP_VERSION, UPDATE_INFO_URL

logger = logging.getLogger(__name__)


def check_for_updates():
    """
    Sunucudaki versiyon bilgisini kontrol eder ve bir güncelleme olup olmadığını döndürür.
    """
    logger.info(f"Güncellemeler kontrol ediliyor. Mevcut Sürüm: {APP_VERSION}, Sunucu: {UPDATE_INFO_URL}")
    try:
        response = requests.get(UPDATE_INFO_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        latest_version_str = data.get("latest_version")
        download_url = data.get("download_url")

        if not latest_version_str or not download_url:
            logger.error("Sunucudan gelen versiyon bilgisi eksik veya bozuk.")
            return {'update_available': False}

        current_version = parse_version(APP_VERSION)
        latest_version = parse_version(latest_version_str)

        if latest_version > current_version:
            logger.info(f"Yeni sürüm bulundu: {latest_version_str}")
            return {
                'update_available': True,
                'latest_version': latest_version_str,
                'download_url': download_url,
                'release_notes': data.get('release_notes', 'Sürüm notu bulunamadı.')
            }
        else:
            logger.info("Program güncel.")
            return {'update_available': False}

    except requests.exceptions.RequestException as e:
        logger.error(f"Güncelleme sunucusuna bağlanılamadı: {e}")
        return {'update_available': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Güncelleme kontrolü sırasında beklenmedik hata: {e}", exc_info=True)
        return {'update_available': False, 'error': str(e)}

# Not: Gerçek indirme ve güncelleme mantığı (updater.exe çalıştırma)
# bir sonraki aşamada eklenecektir.