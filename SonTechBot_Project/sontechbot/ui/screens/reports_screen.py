import datetime
import logging
import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

from ...core import synchronizer
from ...erp_integrations import ERP12Handler
from ...repositories import issue_repo, settings_repo
from ..helpers import (RENK_BUTON_GRI_ARKA, RENK_BUTON_MAVI_ARKA,
                       RENK_BUTON_TURUNCU_ARKA, RENK_BUTON_YESIL_ARKA,
                       RENK_HEADER_ARKA, RENK_HEADER_YAZI, RENK_LOG_YAZI,
                       create_styled_button)
from ..popups.error_reports_popup import ErrorDetailPopup

logger = logging.getLogger(__name__)

try:
    import openpyxl
    EXCEL_EXPORT_ENABLED = True
except ImportError:
    EXCEL_EXPORT_ENABLED = False


class ReportsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_filter = 0
        self.price_inputs = {}
        self.unpriced_products = []
        self.issue_rows = {}

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        tab_panel = TabbedPanel(do_default_tab=False, tab_width=dp(200), tab_pos='top_left')

        error_tab = TabbedPanelItem(text='Hata Raporları')
        error_tab.add_widget(self.build_error_reports_tab())
        tab_panel.add_widget(error_tab)

        unpriced_tab = TabbedPanelItem(text='Fiyatı Olmayan Ürünler')
        unpriced_tab.add_widget(self.build_unpriced_products_tab())
        tab_panel.add_widget(unpriced_tab)

        tab_panel.default_tab = error_tab
        main_layout.add_widget(tab_panel)
        self.add_widget(main_layout)

    def on_enter(self, *args):
        self.load_issues()
        self.load_unpriced_products()

    def build_error_reports_tab(self):
        layout = BoxLayout(orientation='vertical', spacing=dp(10))
        filter_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        self.unresolved_btn = create_styled_button("Çözülmemiş", lambda x: self.set_filter(0), background_color=RENK_BUTON_MAVI_ARKA)
        self.resolved_btn = create_styled_button("Çözülmüş", lambda x: self.set_filter(1), background_color=RENK_BUTON_GRI_ARKA)
        self.all_btn = create_styled_button("Tümü", lambda x: self.set_filter(2), background_color=RENK_BUTON_GRI_ARKA)
        filter_layout.add_widget(self.unresolved_btn)
        filter_layout.add_widget(self.resolved_btn)
        filter_layout.add_widget(self.all_btn)
        layout.add_widget(filter_layout)

        header_layout = GridLayout(cols=6, size_hint_y=None, height=dp(40), spacing=dp(5))
        headers = ["Zaman", "Tür", "Barkod", "Şube", "Mesaj", "Aksiyonlar"]
        col_widths = [0.15, 0.15, 0.15, 0.15, 0.25, 0.15]
        for i, text in enumerate(headers):
            header_label = Label(text=text, color=RENK_HEADER_YAZI, font_size=dp(14), bold=True, size_hint_x=col_widths[i], halign='center')
            with header_label.canvas.before:
                Color(rgba=RENK_HEADER_ARKA)
                header_label.rect = Rectangle(size=header_label.size, pos=header_label.pos)
            header_label.bind(size=lambda i, v: setattr(i.rect, 'size', v), pos=lambda i, v: setattr(i.rect, 'pos', v))
            header_layout.add_widget(header_label)
        layout.add_widget(header_layout)

        scrollview = ScrollView(size_hint=(1, 1), bar_width=dp(10))
        self.issues_layout = GridLayout(cols=1, spacing=dp(2), size_hint_y=None, row_default_height=dp(40))
        self.issues_layout.bind(minimum_height=self.issues_layout.setter('height'))
        scrollview.add_widget(self.issues_layout)
        layout.add_widget(scrollview)
        return layout

    def set_filter(self, filter_type):
        self.current_filter = filter_type
        self.unresolved_btn.md_bg_color = RENK_BUTON_MAVI_ARKA if filter_type == 0 else RENK_BUTON_GRI_ARKA
        self.resolved_btn.md_bg_color = RENK_BUTON_MAVI_ARKA if filter_type == 1 else RENK_BUTON_GRI_ARKA
        self.all_btn.md_bg_color = RENK_BUTON_MAVI_ARKA if filter_type == 2 else RENK_BUTON_GRI_ARKA
        self.load_issues()

    def load_issues(self, *args):
        if hasattr(self, 'issues_layout'):
            threading.Thread(target=self._run_load_issues, daemon=True).start()

    def _run_load_issues(self):
        if self.current_filter == 0:
            issues_to_load = issue_repo.get_all_unresolved_issues()
        elif self.current_filter == 1:
            issues_to_load = issue_repo.get_all_resolved_issues()
        else:
            issues_to_load = issue_repo.get_all_issues()
        Clock.schedule_once(lambda dt: self.populate_issues_ui(issues_to_load))

    def populate_issues_ui(self, issues_to_load):
        self.issues_layout.clear_widgets()
        self.issue_rows.clear()
        if not issues_to_load:
            self.issues_layout.add_widget(Label(text="Gösterilecek sorun bulunamadı.", size_hint_y=None, height=dp(50)))
            return

        col_widths = [0.15, 0.15, 0.15, 0.15, 0.25, 0.15]
        for issue in issues_to_load:
            row = GridLayout(cols=6, size_hint_y=None, height=dp(40), spacing=dp(5))
            try:
                formatted_time = datetime.datetime.strptime(issue.get("timestamp", ""), '%Y-%m-%d %H:%M:%S').strftime('%d.%m %H:%M')
            except (ValueError, TypeError):
                formatted_time = issue.get("timestamp", "")

            row.add_widget(Label(text=formatted_time, font_size=dp(12), color=RENK_LOG_YAZI, size_hint_x=col_widths[0]))
            row.add_widget(Label(text=str(issue.get("issue_type", "")), font_size=dp(12), color=RENK_LOG_YAZI, size_hint_x=col_widths[1]))
            row.add_widget(Label(text=str(issue.get("barcode", "")), font_size=dp(12), color=RENK_LOG_YAZI, size_hint_x=col_widths[2]))
            row.add_widget(Label(text=str(issue.get("erp_branch_name", "")), font_size=dp(12), color=RENK_LOG_YAZI, size_hint_x=col_widths[3]))
            msg_label = Label(text=str(issue.get("message", "")), font_size=dp(12), color=RENK_LOG_YAZI, size_hint_x=col_widths[4], halign='left', valign='top', shorten=True, ellipsis_options={'color': (1, 0.2, 0.2, 1)})
            msg_label.bind(width=lambda instance, width: setattr(instance, 'text_size', (width * 0.95, None)))
            row.add_widget(msg_label)

            action_layout = BoxLayout(orientation='horizontal', size_hint_x=col_widths[5], spacing=dp(5))
            detail_button = create_styled_button("Detay", lambda x, i=issue: self.show_issue_details(i), background_color=RENK_BUTON_MAVI_ARKA, font_size=dp(10), height=dp(30))
            action_layout.add_widget(detail_button)

            if not issue.get('is_resolved'):
                resolve_button = create_styled_button("Çözüldü", lambda x, issue_id=issue['id'], r_widget=row: self.mark_issue_resolved_handler(issue_id, r_widget), background_color=RENK_BUTON_YESIL_ARKA, font_size=dp(10), height=dp(30))
                action_layout.add_widget(resolve_button)
            row.add_widget(action_layout)

            self.issues_layout.add_widget(row)
            self.issue_rows[issue['id']] = row

    def show_issue_details(self, issue_data):
        ErrorDetailPopup(issue_data=issue_data).open()

    def mark_issue_resolved_handler(self, issue_id, row_widget):
        threading.Thread(target=self._run_mark_resolved_in_background, args=(issue_id, row_widget), daemon=True).start()

    def _run_mark_resolved_in_background(self, issue_id, row_widget):
        if issue_repo.mark_issue_resolved(issue_id):
            Clock.schedule_once(lambda dt: self.issues_layout.remove_widget(row_widget))
        else:
            dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
            Clock.schedule_once(lambda dt: dashboard.add_log_message(f"HATA: ID {issue_id} çözüldü olarak işaretlenemedi."))

    def build_unpriced_products_tab(self):
        from ..helpers import create_styled_textinput
        layout = BoxLayout(orientation='vertical', spacing=dp(10))
        header = GridLayout(cols=6, size_hint_y=None, height=dp(40), spacing=dp(5))
        headers = ["Barkod", "Ürün Adı", "ERP Stok", "Şube", "Yeni Fiyat", "Kaydet?"]
        col_widths = [0.18, 0.32, 0.1, 0.15, 0.15, 0.1]
        for i, h_text in enumerate(headers):
            h_label = Label(text=h_text, color=RENK_HEADER_YAZI, font_size=dp(14), bold=True, size_hint_x=col_widths[i], halign='center')
            with h_label.canvas.before:
                Color(rgba=RENK_HEADER_ARKA)
                h_label.rect = Rectangle(size=h_label.size, pos=h_label.pos)
            h_label.bind(size=lambda i, v: setattr(i.rect, 'size', v), pos=lambda i, v: setattr(i.rect, 'pos', v))
            header.add_widget(h_label)
        layout.add_widget(header)

        scroll = ScrollView(bar_width=dp(10))
        self.products_layout = GridLayout(cols=1, spacing=dp(2), size_hint_y=None, row_default_height=dp(45))
        self.products_layout.bind(minimum_height=self.products_layout.setter('height'))
        scroll.add_widget(self.products_layout)
        layout.add_widget(scroll)

        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10), padding=(0, dp(5)))
        if EXCEL_EXPORT_ENABLED:
            buttons.add_widget(create_styled_button("Excel'e Aktar", self.export_to_excel, background_color=RENK_BUTON_YESIL_ARKA, size_hint_x=0.4))
        self.update_erp_button = create_styled_button("Seçili Fiyatları ERP'ye Yaz", self.update_prices_in_erp_handler, background_color=RENK_BUTON_TURUNCU_ARKA, size_hint_x=0.6)
        buttons.add_widget(self.update_erp_button)
        layout.add_widget(buttons)
        return layout

    def load_unpriced_products(self):
        if hasattr(self, 'products_layout'):
            self.unpriced_products = synchronizer.get_unpriced_products_with_stock()
            self.populate_unpriced_products_ui()

    def populate_unpriced_products_ui(self):
        from ..helpers import create_styled_textinput
        self.products_layout.clear_widgets()
        self.price_inputs.clear()

        if not self.unpriced_products:
            self.products_layout.add_widget(Label(text="Fiyatı olmayan ürün bulunamadı."))
            return

        col_widths = [0.18, 0.32, 0.1, 0.15, 0.15, 0.1]
        for product in self.unpriced_products:
            erp_id = str(product.get("erp_product_id", ""))
            row = GridLayout(cols=6, size_hint_y=None, height=dp(45), spacing=dp(5))

            row.add_widget(Label(text=str(product.get("barcode1", "")), size_hint_x=col_widths[0]))
            name_label = Label(text=str(product.get("name", "")), size_hint_x=col_widths[1], halign='left', shorten=True)
            name_label.bind(width=lambda instance, width: setattr(instance, 'text_size', (width, None)))
            row.add_widget(name_label)
            row.add_widget(Label(text=str(int(product.get("erp_stock_quantity", 0))), halign='center', size_hint_x=col_widths[2]))
            row.add_widget(Label(text=str(product.get("erp_branch_name", "")), size_hint_x=col_widths[3]))
            price_input = create_styled_textinput(hint_text="Fiyat Gir", input_filter='float', size_hint_x=col_widths[4], halign='center')
            save_checkbox = CheckBox(size_hint_x=col_widths[5])
            row.add_widget(price_input)
            row.add_widget(save_checkbox)

            self.products_layout.add_widget(row)
            self.price_inputs[erp_id] = {'input': price_input, 'checkbox': save_checkbox, 'row_widget': row}

    def update_prices_in_erp_handler(self, instance):
        updates = []
        dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')

        price_list_id = settings_repo.get_app_setting("selected_trendyol_price_list_id")

        if not price_list_id:
            dashboard.add_log_message("HATA: ERP Fiyat Listesi ID'si ayarlardan okunamadı!")
            return

        for erp_id, widgets in self.price_inputs.items():
            if widgets['checkbox'].active:
                try:
                    new_price = float(widgets['input'].text.strip().replace(',', '.'))
                    if new_price > 0:
                        updates.append({"erp_product_id": erp_id, "new_price": new_price, "price_list_id": price_list_id})
                except ValueError:
                    continue

        if updates:
            self.update_erp_button.disabled = True
            threading.Thread(target=self.run_erp_price_update, args=(updates,), daemon=True).start()
        else:
            dashboard.add_log_message("UYARI: ERP'ye yazılacak seçili ürün bulunamadı.")

    def run_erp_price_update(self, updates_to_perform):
        dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
        Clock.schedule_once(lambda dt: dashboard.add_log_message(f"ERP'ye {len(updates_to_perform)} adet fiyat güncellemesi gönderiliyor..."))

        erp_updater = ERP12Handler()
        if erp_updater.update_product_prices_in_erp(updates_to_perform):
            Clock.schedule_once(lambda dt: dashboard.add_log_message(f"BAŞARILI: {len(updates_to_perform)} fiyat ERP'de güncellendi."))
            updated_ids = [item['erp_product_id'] for item in updates_to_perform]
            Clock.schedule_once(lambda dt: self._remove_priced_products_from_ui(updated_ids))
        else:
            Clock.schedule_once(lambda dt: dashboard.add_log_message("HATA: Fiyatlar güncellenirken sorun oluştu."))

        Clock.schedule_once(lambda dt: setattr(self.update_erp_button, 'disabled', False))

    def _remove_priced_products_from_ui(self, updated_ids):
        for erp_id in updated_ids:
            if erp_id in self.price_inputs:
                row_to_remove = self.price_inputs[erp_id]['row_widget']
                self.products_layout.remove_widget(row_to_remove)
                del self.price_inputs[erp_id]

    def export_to_excel(self, instance):
        if not EXCEL_EXPORT_ENABLED:
            dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
            dashboard.add_log_message("Excel'e aktarma için 'openpyxl' kütüphanesi gerekli.")
            return

        dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
        try:
            # DÜZELTİLMİŞ KISIM: Kullanıcının Belgelerim klasörüne kaydet
            documents_path = os.path.join(os.path.expanduser("~"), "Documents")
            reports_dir = os.path.join(documents_path, "SonTechBot Raporlar")
            
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
            
            file_name = f"fiyati_olmayan_urunler_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_path = os.path.join(reports_dir, file_name)

            wb = openpyxl.Workbook()
            sheet = wb.active
            sheet.title = "Fiyatsız Ürünler"
            sheet.append(["Barkod", "Ürün Adı", "ERP Ürün ID", "ERP Stok", "Şube Adı", "Yeni Fiyat"])
            
            for product in self.unpriced_products:
                sheet.append([
                    product.get("barcode1"), product.get("name"), product.get("erp_product_id"),
                    product.get("erp_stock_quantity"), product.get("erp_branch_name")
                ])
            
            wb.save(save_path)
            dashboard.add_log_message(f"Liste '{file_name}' olarak Belgeler klasörünüze aktarıldı.")
            
        except Exception as e:
            dashboard.add_log_message(f"Excel'e aktarma hatası: {e}")
            logger.error("Excel'e aktarma hatası", exc_info=True)