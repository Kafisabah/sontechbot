# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 05:30
# Yapılan Değişiklikler:
# 1. Ayarlar ekranındaki marka eşleştirme özelliği için, ERP'den tüm marka adlarını çeken 'get_all_erp_brands' fonksiyonu eklendi.
# 2. Kodun okunabilirliği ve hata yönetimi iyileştirildi.

import datetime
import logging
import traceback

import pyodbc

from ..repositories import settings_repo

logger = logging.getLogger(__name__)


class ERP12Handler:
    def _find_best_sql_driver(self):
        """
        Sistemde yüklü ODBC sürücülerini tarar ve SQL Server için en uygun olanı bulur.
        """
        logger.info("Kullanılabilir ODBC sürücüleri taranıyor...")
        installed_drivers = [d for d in pyodbc.drivers()]
        logger.debug(f"Bulunan sürücüler: {installed_drivers}")
        driver_priority = [
            'ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server',
            'ODBC Driver 13 for SQL Server', 'SQL Server Native Client 11.0', 'SQL Server'
        ]
        for driver in driver_priority:
            if driver in installed_drivers:
                logger.info(f"En uygun SQL Server sürücüsü bulundu: '{driver}'")
                return driver
        logger.error("Sistemde uyumlu hiçbir SQL Server ODBC sürücüsü bulunamadı.")
        raise ConnectionError("Uyumlu SQL Server ODBC sürücüsü bulunamadı. Lütfen sürücülerinizi kontrol edin.")

    def __init__(self, erp_config_override=None):
        self.conn = None
        self.cursor = None
        self.erp_config = erp_config_override or settings_repo.get_erp_config()
        logger.info(f"ERP Config yüklendi: Server={self.erp_config.get('server')}, DB={self.erp_config.get('database')}")
        try:
            driver_value = self._find_best_sql_driver()
        except ConnectionError as e:
            logger.critical(e)
            self.db_connection_string = None
            return
        
        server_value = str(self.erp_config.get('server', ''))
        database_value = str(self.erp_config.get('database', ''))
        username_value = str(self.erp_config.get('username', ''))
        password_value = str(self.erp_config.get('password', ''))
        
        base_connection_parts = [
            f"DRIVER={{{driver_value}}}", f"SERVER={server_value}",
            f"DATABASE={database_value}", "TrustServerCertificate=yes"
        ]
        
        if not username_value and not password_value:
            base_connection_parts.append("Trusted_Connection=yes")
        else:
            if username_value: base_connection_parts.append(f"UID={username_value}")
            if password_value: base_connection_parts.append(f"PWD={password_value}")
            
        self.db_connection_string = ";".join(filter(None, base_connection_parts))
        if self.db_connection_string and not self.db_connection_string.endswith(';'):
            self.db_connection_string += ";"

    def test_connection(self):
        connection_string_to_log = self.db_connection_string
        if not connection_string_to_log:
            return False, "Sürücü bulunamadığı için bağlantı dizesi oluşturulamadı."
            
        current_password = self.erp_config.get('password', '')
        if current_password and f"PWD={current_password}" in connection_string_to_log:
            connection_string_to_log = connection_string_to_log.replace(
                f"PWD={current_password}", "PWD=********")

        logger.info(f"ERP Test bağlantısı deneniyor: {connection_string_to_log}")

        if not self.erp_config.get('server') or not self.erp_config.get('database'):
            message = "Hata: Sunucu ve Veritabanı adları boş olamaz."
            logger.warning(f"ERP Test başarısız: {message}")
            return False, message

        try:
            test_conn = pyodbc.connect(self.db_connection_string, timeout=5)
            cursor = test_conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            test_conn.close()
            logger.info("ERP Test bağlantısı başarılı.")
            return True, "Bağlantı başarılı!"
        except pyodbc.Error as ex:
            error_message = f"Bağlantı Hatası: {ex}"
            logger.error(f"ERP Test bağlantısı başarısız: {error_message}")
            return False, error_message
        except Exception as e:
            error_message = f"Beklenmedik Hata: {e}"
            logger.error(f"ERP Test sırasında beklenmedik hata: {error_message}", exc_info=True)
            return False, error_message

    def _connect_erp_db(self):
        if not self.db_connection_string:
            logger.error("Bağlantı dizesi mevcut değil, bağlantı kurulamıyor.")
            return False
            
        if not self.erp_config.get('server') or not self.erp_config.get('database'):
            logger.error("ERP bağlantı ayarlarında eksik bilgi var (Server, Database).")
            return False

        try:
            self.conn = pyodbc.connect(self.db_connection_string, timeout=10)
            self.cursor = self.conn.cursor()
            return True
        except pyodbc.Error as ex:
            logger.error(f"ERP veritabanı bağlantısı başarısız: {ex}", exc_info=True)
            self.conn = None
            self.cursor = None
            return False
        except Exception as e:
            logger.error(f"ERP bağlantısı sırasında beklenmedik bir hata oluştu: {e}", exc_info=True)
            self.conn = None
            self.cursor = None
            return False

    def _close_erp_db(self):
        if self.cursor:
            try: self.cursor.close()
            except Exception: pass
            self.cursor = None
        if self.conn:
            try: self.conn.close()
            except Exception: pass
            self.conn = None

    def get_products_from_erp_for_branch(self, branch_map):
        if not self._connect_erp_db():
            logger.error("ERP bağlantısı kurulamadığı için ürün çekilemedi.")
            return []

        location_id_str = branch_map.get("erp_location_id")
        price_list_id_str = branch_map.get("erp_price_list_id")

        if not location_id_str or not price_list_id_str:
            logger.warning("Şube lokasyon veya fiyat listesi ID'si eksik.")
            self._close_erp_db()
            return []

        try:
            param_location_id = int(location_id_str)
            param_price_list_id = int(price_list_id_str)
        except (ValueError, TypeError) as ve:
            logger.error(f"ID'ler ({location_id_str}, {price_list_id_str}) tamsayıya çevrilemedi: {ve}")
            self._close_erp_db()
            return []

        logger.info(f"Lokasyon ID: {location_id_str}, Fiyat Liste ID: {price_list_id_str} için STOKLU ürünler çekiliyor...")

        sql_query = """
        SELECT
            s.ID AS erp_product_id, s.KOD AS stok_kod, s.AD AS name,
            (SELECT MIN(sb.BARKOD) FROM dbo.STOK_BARKOD sb
             INNER JOIN dbo.STOK_STOK_BIRIM ssb_b1 ON sb.STOK_STOK_BIRIM = ssb_b1.ID
             WHERE ssb_b1.STOK = s.ID AND ssb_b1.VARSAYILAN = 1) AS barcode1,
            brm.AD AS unit, CAST(ISNULL(v.KDV_PAREKENDE, 0) AS INT) AS vat_rate,
            sg.AD AS erp_grup_kod,
            smk.AD AS erp_marka_adi,
            s.WEBDEYAYINLANIRMI AS web_publish_flag,
            ISNULL((SELECT TOP 1 smiktar.MIKTAR FROM dbo.STOK_MIKTAR smiktar
                    WHERE smiktar.STOK = s.ID AND smiktar.LOKASYON = ?), 0) AS erp_stock_quantity,
            ISNULL((SELECT TOP 1 fiyat.FIYAT FROM dbo.STOK_STOK_BIRIM_FIYAT fiyat
                    INNER JOIN dbo.STOK_STOK_BIRIM ssb_fiyat ON fiyat.STOK_STOK_BIRIM = ssb_fiyat.ID
                    WHERE ssb_fiyat.STOK = s.ID AND ssb_fiyat.VARSAYILAN = 1 AND fiyat.STOK_FIYAT_AD = ?), 0) AS price
        FROM dbo.STOK s
        LEFT JOIN dbo.STOK_STOK_BIRIM ssb ON s.ID = ssb.STOK AND ssb.VARSAYILAN = 1
        LEFT JOIN dbo.STOK_BIRIM brm ON ssb.STOK_BIRIM = brm.ID
        LEFT JOIN dbo.STOK_VERGI v ON s.STOK_VERGI = v.ID
        LEFT JOIN dbo.STOGRUPSEFC sg ON s.STOK_GRUP = sg.ID
        LEFT JOIN dbo.STOK_MARKA smk ON s.STOK_MARKA = smk.ID
        WHERE
            s.WEBDEYAYINLANIRMI = 1
            AND ISNULL((SELECT TOP 1 smiktar.MIKTAR FROM dbo.STOK_MIKTAR smiktar WHERE smiktar.STOK = s.ID AND smiktar.LOKASYON = ?), 0) > 0
        ORDER BY s.ID;
        """
        try:
            self.cursor.execute(sql_query, param_location_id, param_price_list_id, param_location_id)
            rows = self.cursor.fetchall()
            if rows:
                columns = [column[0] for column in self.cursor.description]
                fetched_data = [dict(zip(columns, r)) for r in rows]
                logger.info(f"{len(fetched_data)} adet STOKLU ürün çekildi.")
                return fetched_data
            return []
        except pyodbc.Error as ex:
            branch_name = branch_map.get('erp_branch_name')
            logger.error(f"ERP'den '{branch_name}' için veri çekerken SQL HATA: {ex}", exc_info=True)
            return []
        finally:
            self._close_erp_db()

    def get_all_erp_price_lists(self):
        if not self._connect_erp_db(): return []
        price_lists = []
        sql_query = "SELECT ID, AD FROM dbo.STOK_FIYAT_ADLARI ORDER BY AD;"
        try:
            self.cursor.execute(sql_query)
            rows = self.cursor.fetchall()
            if rows:
                columns = [c[0] for c in self.cursor.description]
                price_lists = [dict(zip(columns, r)) for r in rows]
                logger.info(f"{len(price_lists)} adet fiyat listesi çekildi.")
        except pyodbc.Error as ex:
            logger.error(f"ERP'den fiyat listelerini çekerken SQL HATA: {ex}")
        finally:
            self._close_erp_db()
        return price_lists

    def get_all_erp_locations(self):
        if not self._connect_erp_db(): return []
        locations = []
        sql_query = "SELECT ID, AD FROM dbo.TR_LOKASYON ORDER BY AD;"
        try:
            self.cursor.execute(sql_query)
            rows = self.cursor.fetchall()
            if rows:
                columns = [c[0] for c in self.cursor.description]
                locations = [dict(zip(columns, r)) for r in rows]
                logger.info(f"{len(locations)} adet lokasyon çekildi.")
        except pyodbc.Error as ex:
            logger.error(f"ERP'den lokasyonları çekerken SQL HATA: {ex}")
        finally:
            self._close_erp_db()
        return locations

    def get_all_erp_categories(self):
        if not self._connect_erp_db(): return []
        categories = []
        sql_query = "SELECT ID, AD FROM dbo.STOGRUPSEFC ORDER BY AD;"
        try:
            self.cursor.execute(sql_query)
            rows = self.cursor.fetchall()
            if rows:
                columns = [c[0] for c in self.cursor.description]
                categories = [dict(zip(columns, r)) for r in rows]
                logger.info(f"{len(categories)} adet kategori çekildi.")
        except pyodbc.Error as ex:
            logger.error(f"ERP'den kategorileri çekerken SQL HATA: {ex}")
        finally:
            self._close_erp_db()
        return categories

    def get_all_erp_brands(self):
        """
        ERP veritabanından tüm marka tanımlarını çeker.
        """
        if not self._connect_erp_db():
            return []
        brands = []
        # Not: Bu sorgu sizin ERP yapınıza göre değişebilir.
        # Genellikle markaların tutulduğu bir 'MARKA' veya benzeri bir tablo olur.
        sql_query = "SELECT ID, AD FROM dbo.STOK_MARKA WHERE AD IS NOT NULL AND AD != '' ORDER BY AD;"
        try:
            self.cursor.execute(sql_query)
            rows = self.cursor.fetchall()
            if rows:
                columns = [c[0] for c in self.cursor.description]
                brands = [dict(zip(columns, r)) for r in rows]
                logger.info(f"{len(brands)} adet ERP markası çekildi.")
        except pyodbc.Error as ex:
            logger.error(f"ERP'den markaları çekerken SQL HATA: {ex}")
        finally:
            self._close_erp_db()
        return brands

    def update_product_prices_in_erp(self, price_updates_list):
        if not price_updates_list: return True
        if not self._connect_erp_db(): return False
        logger.info(f"{len(price_updates_list)} adet ürün için fiyat güncelleme işlemi başlıyor...")
        success_count, failure_count = 0, 0
        try:
            for update_item in price_updates_list:
                erp_product_id = int(update_item.get("erp_product_id"))
                new_price = float(update_item.get("new_price"))
                price_list_id = int(update_item.get("price_list_id"))
                if not all([erp_product_id, new_price > 0, price_list_id]):
                    failure_count += 1
                    continue
                update_sql = """
                UPDATE dbo.STOK_STOK_BIRIM_FIYAT
                SET FIYAT = ?
                WHERE STOK_FIYAT_AD = ?
                AND STOK_STOK_BIRIM = (SELECT ID FROM dbo.STOK_STOK_BIRIM WHERE STOK = ? AND VARSAYILAN = 1)
                """
                self.cursor.execute(update_sql, new_price, price_list_id, erp_product_id)
                success_count += 1
            if failure_count == 0:
                self.conn.commit()
                logger.info(f"BAŞARILI: {success_count} adet fiyat güncellemesi ERP veritabanına işlendi.")
                return True
            else:
                self.conn.rollback()
                logger.warning(f"BAŞARISIZ: {failure_count} geçersiz veri nedeniyle değişiklikler geri alındı.")
                return False
        except (pyodbc.Error, ValueError) as ex:
            self.conn.rollback()
            logger.error(f"ERP güncelleme sırasında SQL/Veri Hatası: {ex}", exc_info=True)
            return False
        finally:
            self._close_erp_db()
