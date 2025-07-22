# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 06.07.2025 07:15
# Yapılan Değişiklikler:
# 1. Tüm online lisans kontrolü ve MAC adresi mantığı devre dışı bırakıldı.
# 2. Fonksiyonlar artık geliştirme ve dağıtım kolaylığı için her zaman 'geçerli' bir lisans durumu döndürüyor.
# 3. Bu dosya, gelecekte lisanslama sistemi yeniden aktif edileceği zaman eski mantığın geri getirilebilmesi için korunmuştur.

import logging

logger = logging.getLogger(__name__)

def get_machine_id():
    """
    PASİF HALE GETİRİLDİ.
    Geliştirme sürecinde makine kimliği kontrolü yapmaz.
    """
    logger.info("get_machine_id çağrıldı (Pasif Mod).")
    return "developer-machine-id"

def save_license_data(license_data):
    """PASİF HALE GETİRİLDİ. Lisans verisini kaydetmez."""
    logger.info("save_license_data çağrıldı (Pasif Mod).")
    return True

def load_license_data():
    """PASİF HALE GETİRİLDİ. Yerel lisans verisini okumaz."""
    logger.info("load_license_data çağrıldı (Pasif Mod).")
    return {}

def activate_license(email, key):
    """
    PASİF HALE GETİRİLDİ.
    Aktivasyon denemesi yapmaz, her zaman başarılı döner.
    """
    logger.info(f"activate_license çağrıldı (Pasif Mod): email={email}")
    return {'status': 'valid', 'message': 'Geliştirici modu aktivasyonu.'}

def check_license_status():
    """
    PASİF HALE GETİRİLDİ.
    Programın ana lisans kontrol fonksiyonu. Her zaman geçerli bir lisans durumu döndürür.
    """
    logger.warning("Lisans kontrolü 'check_license_status' çağrıldı (Pasif Mod). Her zaman 'valid' dönecek.")
    return {
        'status': 'valid', 
        'message': 'Lisans kontrolü geliştirme için devre dışı bırakıldı.'
    }
