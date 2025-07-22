# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 05:50
# Yapılan Değişiklikler:
# 1. 'AttributeError' hatasını çözmek için eksik olan 'get_trendyol_categories' ve 'get_trendyol_brands' fonksiyonları eklendi.
# 2. Bu dosya, dökümanlara uygun olarak Trendyol GO API'si ile tam uyumlu hale getirilmiştir.

import json
import logging
import requests

logger = logging.getLogger(__name__)


class TrendyolGoAPI:
    """
    Trendyol GO (Hızlı Market) API'si ile iletişim kurmak için yazılmış sınıftır.
    """
    def __init__(self, supplier_id, api_key, api_secret, base_url,
                 test_mode_enabled=False):
        self.supplier_id = supplier_id
        self.api_key = api_key
        self.api_secret = api_secret
        
        self.base_url = "https://stageapi.tgoapis.com" if test_mode_enabled else "https://api.tgoapis.com"
        self.test_mode_enabled = test_mode_enabled

        self.headers = {
            "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "SonTechBot/1.8.0", "api-key": self.api_key,
            "x-api-secret-key": self.api_secret
        }
        logger.info(
            f"TrendyolGoAPI başlatıldı. Supplier ID: {self.supplier_id}, "
            f"Base URL: {self.base_url}"
        )

    def _make_request(self, method, endpoint, params=None, data=None):
        """Tüm Trendyol API isteklerini yapan ve ağ hatalarını yöneten merkezi fonksiyondur."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"API Request: {method.upper()} {url}")
        if data: logger.debug(f"Payload: {json.dumps(data, indent=2)}")
        try:
            response = requests.request(method, url, params=params, json=data, headers=self.headers, timeout=45)
            logger.debug(f"Response Status: {response.status_code}")
            try:
                json_response = response.json()
                if not response.ok:
                    return {"status": "error", "message": f"HTTP Hatası: {response.status_code}", "details": json_response}
                return json_response
            except json.JSONDecodeError:
                return {"status": "error", "message": f"JSON olmayan yanıt (HTTP {response.status_code})", "details": response.text}
        except requests.exceptions.RequestException as e:
            user_friendly_message = "Ağ Hatası: Sunucuya ulaşılamadı. İnternet/DNS ayarlarınızı veya Güvenlik Duvarı'nı kontrol edin."
            logger.error(f"API bağlantı hatası: {e}", exc_info=True)
            return {"status": "error", "message": user_friendly_message}

    def test_connection(self):
        """API bağlantısını test etmek için dökümandaki yapıya uygun bir endpoint kullanır."""
        logger.info("Trendyol API bağlantı testi başlatılıyor...")
        endpoint = f"/integrator/suppliers/{self.supplier_id}/warehouses"
        response = self._make_request("GET", endpoint)

        if isinstance(response, list):
            logger.info("Trendyol API bağlantı testi başarılı.")
            return True, "Bağlantı başarılı!"
        elif isinstance(response, dict) and 'errors' in response:
            error_message = response['errors'][0].get("message", "Bilinmeyen API hatası.")
            logger.error(f"Bağlantı testi başarısız: {error_message}")
            return False, f"Bağlantı Başarısız: {error_message}"
        else:
            error_message = response.get("message", "Beklenmedik bir yanıt alındı.")
            logger.error(f"Bağlantı testinde beklenmedik yanıt: {response}")
            return False, error_message

    def get_trendyol_categories(self):
        """Trendyol GO API'sinden tüm kategorileri sayfa sayfa çeker ve birleştirir."""
        all_categories = []
        page = 0
        size = 200
        endpoint = "/integrator/product/grocery/categories"
        while True:
            logger.info(f"Trendyol kategorileri çekiliyor... Sayfa: {page + 1}")
            params = {"page": page, "size": size}
            response = self._make_request("GET", endpoint, params=params)
            if response and isinstance(response, list):
                all_categories.extend(response)
                if len(response) < size: break
                page += 1
            else:
                logger.error(f"Kategoriler çekilirken {page}. sayfada beklenmedik yanıt veya hata: {response}")
                break
        logger.info(f"Toplam {len(all_categories)} adet Trendyol kategorisi çekildi.")
        return all_categories

    def get_trendyol_brands(self):
        """Trendyol GO API'sinden tüm markaları sayfa sayfa çeker ve birleştirir."""
        all_brands = []
        page = 0
        size = 200
        endpoint = "/integrator/product/grocery/brands"
        while True:
            logger.info(f"Trendyol markaları çekiliyor... Sayfa: {page + 1}")
            params = {"page": page, "size": size}
            response = self._make_request("GET", endpoint, params=params)
            if response and isinstance(response, dict) and 'brands' in response:
                brands_on_page = response['brands']
                all_brands.extend(brands_on_page)
                if len(brands_on_page) < size: break
                page += 1
            else:
                logger.error(f"Markalar çekilirken {page}. sayfada beklenmedik yanıt veya hata: {response}")
                break
        logger.info(f"Toplam {len(all_brands)} adet Trendyol markası çekildi.")
        return all_brands
        
    def update_stock_price(self, product_updates):
        """Stok ve fiyat güncellemek için dökümandaki doğru endpoint'i kullanır."""
        if not product_updates: return None
        endpoint = f"/integrator/product/grocery/suppliers/{self.supplier_id}/products/price-and-inventory"
        payload = {"items": product_updates}
        return self._make_request("POST", endpoint, data=payload)

    def check_batch_request_status(self, batch_request_id):
        """Toplu işlem durumunu kontrol etmek için dökümandaki doğru endpoint'i kullanır."""
        logger.info(f"Toplu işlem durumu kontrol ediliyor: Batch ID = {batch_request_id}")
        endpoint = f"/integrator/product/grocery/suppliers/{self.supplier_id}/batch-requests/{batch_request_id}"
        return self._make_request("GET", endpoint)
