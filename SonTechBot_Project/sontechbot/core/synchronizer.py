# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 09:55
# Yapılan Değişiklikler:
# 1. 'ImportError' hatasını çözmek için, artık kullanılmayan 'brand_repo' import'u kaldırıldı.
# 2. Kod, marka eşleştirmesi olmadan, sadece kategori kurallarına göre çalışacak şekilde sadeleştirildi.

import datetime
import json
import threading
import time
import traceback

from kivy.app import App
from kivy.clock import Clock

from ..ecommerce_integrations.trendyol_handler import TrendyolGoAPI
from ..erp_integrations import ERP12Handler
from ..repositories import (branch_repo, category_repo, history_repo,
                            issue_repo, product_repo, settings_repo)
from ..ui.helpers import LoadingPopup

gui_status_update_callback = None
unpriced_products_with_stock = []
_loading_popup_instance = None

def set_gui_status_updater(callback_function):
    global gui_status_update_callback
    gui_status_update_callback = callback_function

def update_gui_status(message):
    if gui_status_update_callback and hasattr(gui_status_update_callback, '__call__'):
        Clock.schedule_once(lambda dt: gui_status_update_callback(message), 0)
    else:
        print(f"[SYNC STATUS] {message}")

def get_unpriced_products_with_stock():
    global unpriced_products_with_stock
    return list(unpriced_products_with_stock)

def _show_loading_popup(message="İşlem devam ediyor..."):
    if App.get_running_app():
        global _loading_popup_instance
        if _loading_popup_instance is None: _loading_popup_instance = LoadingPopup(message=message)
        else: _loading_popup_instance.set_message(message)
        _loading_popup_instance.open()

def _hide_loading_popup():
    if App.get_running_app():
        global _loading_popup_instance
        if _loading_popup_instance:
            _loading_popup_instance.dismiss()
            _loading_popup_instance = None

def _process_batch_results(api_client, batch_id, branch_name):
    update_gui_status(f"'{batch_id}' nolu işlemin sonucu kontrol ediliyor...")
    time.sleep(5)
    response = api_client.check_batch_request_status(batch_id)
    
    if response and response.get('status') == 'COMPLETED':
        failed_items = [item for item in response.get('items', []) if item.get('status') == 'FAILURE']
        for item in failed_items:
            error_reason = item.get('failureReasons', ['Bilinmeyen hata'])[0]
            barcode = item.get('requestItem', {}).get('barcode')
            if "not found" in error_reason.lower() or "bulunamadı" in error_reason.lower():
                issue_repo.add_sync_issue(None, barcode, branch_name, "Eşleşmemiş Ürün", error_reason)
            else:
                issue_repo.add_sync_issue(None, barcode, branch_name, "API Güncelleme Hatası", error_reason)
        return len(failed_items)
    elif response and response.get('status') == 'PROCESSING':
        update_gui_status(f"'{batch_id}' nolu işlem hala sürüyor. Daha sonra kontrol edilecek.")
        return 0
    else:
        update_gui_status(f"'{batch_id}' nolu işlemin sonucu alınamadı. Yanıt: {response}")
        return 0

def run_single_sync_cycle(sync_type='manual', on_finish_callback=None):
    global unpriced_products_with_stock
    unpriced_products_with_stock = []
    start_time_obj, start_time_ts = datetime.datetime.now(), time.time()
    Clock.schedule_once(lambda dt: _show_loading_popup(f"'{sync_type.capitalize()}' senkronizasyon başlatılıyor..."), 0)
    update_gui_status(f"'{sync_type.capitalize()}' senkronizasyon döngüsü başlatılıyor...")

    total_products_processed, total_products_sent, total_issues_found = 0, 0, 0
    final_status, summary_message = "Başarısız", "Bilinmeyen bir hata oluştu."
    batch_ids = []

    try:
        erp_handler = ERP12Handler()
        trendyol_cfg = settings_repo.get_trendyol_config()
        if not all(trendyol_cfg.get(k) for k in ['api_key', 'api_secret', 'supplier_id']):
            raise ValueError("Trendyol API ayarları eksik. 'Ayarlar' bölümünü kontrol edin.")

        trendyol_api_client = TrendyolGoAPI(**trendyol_cfg)
        
        category_rules = {str(m['erp_category_id']): m for m in category_repo.get_all_category_rules()}
        active_branches = [b for b in branch_repo.get_all_branch_mappings() if b.get('is_active', True)]
        
        if not active_branches: raise ValueError("Senkronize edilecek aktif şube bulunamadı.")

        for branch in active_branches:
            branch_name = branch.get("erp_branch_name")
            store_id = branch.get("trendyol_store_id")

            if not store_id:
                update_gui_status(f"UYARI: '{branch_name}' için Mağaza ID'si tanımlanmamış. Bu şube atlanıyor.")
                continue

            update_gui_status(f"'{branch_name}' (Mağaza ID: {store_id}) için ürünler çekiliyor...")
            erp_products = erp_handler.get_products_from_erp_for_branch(branch)
            if not erp_products:
                update_gui_status(f"'{branch_name}' için ERP'den stoklu ürün bulunamadı.")
                continue

            products_to_send = []
            
            for product in erp_products:
                total_products_processed += 1
                barcode = str(product.get('barcode1') or '').strip()
                if not barcode: continue

                rule = category_rules.get(str(product.get('erp_grup_kod')))
                if not rule or not rule.get('sync_enabled', True):
                    continue

                price = float(product.get('price', 0)) * (1 + float(rule.get('price_adjustment_percentage', 0.0)) / 100)
                if price <= 0:
                    unpriced_products_with_stock.append(product)
                    issue_repo.add_sync_issue(product.get('erp_product_id'), barcode, branch_name, "Fiyatsız Ürün", f"Fiyat sıfır veya negatif: {price:.2f}")
                    total_issues_found += 1
                    continue

                stock = max(0, int(product.get('erp_stock_quantity', 0)) - int(branch.get('stock_buffer', 0)))
                
                products_to_send.append({
                    "barcode": barcode, "quantity": stock,
                    "sellingPrice": round(price, 2), "originalPrice": round(price, 2),
                    "storeId": store_id
                })

            for i in range(0, len(products_to_send), 50):
                chunk = products_to_send[i:i + 50]
                response = trendyol_api_client.update_stock_price(chunk)
                if response and response.get("batchRequestId"):
                    batch_id = response["batchRequestId"]
                    update_gui_status(f"'{branch_name}' için {len(chunk)} ürün gönderildi. Batch ID: {batch_id}")
                    batch_ids.append((batch_id, branch_name))
                    total_products_sent += len(chunk)
                else:
                    error_msg = response.get("message", "API'den bilinmeyen hata.") if response else "Boş yanıt"
                    update_gui_status(f"HATA: '{branch_name}' için paket gönderilemedi: {error_msg}")
                    total_issues_found += len(chunk)

        if batch_ids:
            update_gui_status("Tüm paketler gönderildi. Sonuçlar kontrol ediliyor...")
            for batch_id, branch_name in batch_ids:
                total_issues_found += _process_batch_results(trendyol_api_client, batch_id, branch_name)
        
        final_status = "Başarılı" if total_issues_found == 0 else "Uyarılarla Tamamlandı"
        summary_message = f"{total_products_processed} ürün işlendi, {total_products_sent} gönderildi, {total_issues_found} sorun."

    except Exception as e:
        final_status, summary_message = "Kritik Hata", f"Döngü durduruldu: {e}"
        update_gui_status(f"[color=ff3333]KRİTİK HATA: {summary_message}[/color]")
        traceback.print_exc()
    finally:
        duration = time.time() - start_time_ts
        history_repo.add_sync_history_entry({
            "start_time": start_time_obj.strftime('%Y-%m-%d %H:%M:%S'), "duration_seconds": round(duration, 2),
            "sync_type": sync_type, "status": final_status, "products_processed": total_products_processed,
            "products_sent": total_products_sent, "issues_found": total_issues_found,
            "summary_message": summary_message, "batch_request_id": batch_ids[0][0] if batch_ids else None
        })
        update_gui_status(f"Döngü tamamlandı. Durum: {final_status}")
        Clock.schedule_once(lambda dt: _hide_loading_popup(), 0.5)
        if on_finish_callback: Clock.schedule_once(lambda dt: on_finish_callback())
