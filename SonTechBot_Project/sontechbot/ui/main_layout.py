import logging
import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader

from ...ecommerce_integrations import TrendyolGoAPI
from ...erp_integrations import ERP12Handler
from ...repositories import branch_repo, category_repo, settings_repo
from ..helpers import (RENK_BUTON_YESIL_ARKA, SPINNER_PLACEHOLDER_TEXTS,
                       create_form_row, create_section_header,
                       create_styled_button, create_styled_textinput)

logger = logging.getLogger(__name__)


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.erp_price_lists_data = []
        self.branch_setting_widgets = {}
        self.category_setting_widgets = {}
        self.selected_price_list_id = None

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        tab_panel = TabbedPanel(do_default_tab=False, tab_width=dp(150), tab_pos='top_left')

        erp_tab = TabbedPanelHeader(text='ERP Ayarları')
        erp_tab.content = self.build_erp_settings_tab()
        tab_panel.add_widget(erp_tab)

        api_tab = TabbedPanelHeader(text='API Ayarları')
        api_tab.content = self.build_api_settings_tab()
        tab_panel.add_widget(api_tab)

        general_tab = TabbedPanelHeader(text='Genel Ayarlar')
        general_tab.content = self.build_general_settings_tab()
        tab_panel.add_widget(general_tab)

        tab_panel.default_tab = erp_tab
        main_layout.add_widget(tab_panel)

        save_button = create_styled_button(
            "Tüm Ayarları Kaydet", self.save_all_settings,
            size_hint_y=None, height=dp(50),
            background_color=RENK_BUTON_YESIL_ARKA
        )
        main_layout.add_widget(save_button)
        self.add_widget(main_layout)

    def on_enter(self, *args):
        self.load_settings()

    def build_erp_settings_tab(self):
        scroll_view = ScrollView(bar_width=dp(10))
        erp_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(15), size_hint_y=None)
        erp_layout.bind(minimum_height=erp_layout.setter('height'))

        erp_layout.add_widget(create_section_header("1. ERP Veritabanı Bağlantısı"))
        erp_form = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, row_default_height=dp(45))
        erp_form.bind(minimum_height=erp_form.setter('height'))

        self.erp_server_input = create_styled_textinput()
        create_form_row(erp_form, 'Sunucu Adresi:', self.erp_server_input)
        self.erp_database_input = create_styled_textinput()
        create_form_row(erp_form, 'Veritabanı Adı:', self.erp_database_input)
        self.erp_driver_input = create_styled_textinput()
        create_form_row(erp_form, 'ODBC Sürücüsü:', self.erp_driver_input)
        self.windows_auth_checkbox = CheckBox(active=True, size_hint_x=None, width=dp(48))
        self.windows_auth_checkbox.bind(active=self.on_windows_auth_changed)
        create_form_row(erp_form, 'Windows Kimlik Doğrulaması:', self.windows_auth_checkbox)
        self.erp_username_input = create_styled_textinput(disabled=True)
        create_form_row(erp_form, 'Kullanıcı Adı:', self.erp_username_input)
        self.erp_password_input = create_styled_textinput(password=True, disabled=True)
        create_form_row(erp_form, 'Şifre:', self.erp_password_input)
        erp_layout.add_widget(erp_form)

        erp_layout.add_widget(create_styled_button("ERP Test & Listeleri Yükle", self.test_erp_connection_and_load_lists))

        price_list_form = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(45))
        self.fiyat_listesi_spinner = Spinner(text=SPINNER_PLACEHOLDER_TEXTS[0], values=[], size_hint_y=None, height=dp(45))
        self.fiyat_listesi_spinner.bind(text=self.on_price_list_selected)
        create_form_row(price_list_form, 'Trendyol Fiyat Listesi:', self.fiyat_listesi_spinner)
        erp_layout.add_widget(price_list_form)

        erp_layout.add_widget(create_section_header("2. Şube Senkronizasyon Ayarları"))
        self.branch_settings_layout = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.branch_settings_layout.bind(minimum_height=self.branch_settings_layout.setter('height'))
        erp_layout.add_widget(self.branch_settings_layout)

        erp_layout.add_widget(create_section_header("3. Kategori Ayarları"))
        self.category_settings_layout = GridLayout(cols=3, spacing=dp(15), size_hint_y=None, row_force_default=True, row_default_height=dp(45))
        self.category_settings_layout.bind(minimum_height=self.category_settings_layout.setter('height'))
        erp_layout.add_widget(self.category_settings_layout)

        scroll_view.add_widget(erp_layout)
        return scroll_view

    def build_api_settings_tab(self):
        api_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        api_layout.add_widget(create_section_header("Trendyol API Bilgileri"))
        api_form_layout = GridLayout(cols=2, spacing=(dp(10), dp(15)), size_hint_y=None, row_default_height=dp(45))
        api_form_layout.bind(minimum_height=api_form_layout.setter('height'))

        self.trendyol_api_key_input = create_styled_textinput()
        create_form_row(api_form_layout, 'API Key:', self.trendyol_api_key_input)
        self.trendyol_api_secret_input = create_styled_textinput(password=True)
        create_form_row(api_form_layout, 'API Secret:', self.trendyol_api_secret_input)
        self.trendyol_supplier_id_input = create_styled_textinput()
        create_form_row(api_form_layout, 'Satıcı ID:', self.trendyol_supplier_id_input)
        self.test_mode_checkbox = CheckBox(active=True)
        create_form_row(api_form_layout, 'Test Modunu Aktif Et:', self.test_mode_checkbox)

        api_layout.add_widget(api_form_layout)
        api_test_button = create_styled_button("API Bağlantısını Test Et", self.test_api_connection)
        api_layout.add_widget(api_test_button)
        api_layout.add_widget(Label(size_hint_y=1))
        return api_layout

    def build_general_settings_tab(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        form = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, row_default_height=dp(45))
        form.bind(minimum_height=form.setter('height'))

        self.sync_interval_input = create_styled_textinput(text="15", input_filter='int')
        create_form_row(form, 'Otomatik Senk. Aralığı (Dakika):', self.sync_interval_input)

        layout.add_widget(form)
        layout.add_widget(Label(size_hint_y=1))
        return layout

    def on_windows_auth_changed(self, checkbox, value):
        self.erp_username_input.disabled = value
        self.erp_password_input.disabled = value
        if value:
            self.erp_username_input.text = ""
            self.erp_password_input.text = ""

    def load_settings(self):
        threading.Thread(target=self._run_load_settings, daemon=True).start()

    def _run_load_settings(self):
        erp_cfg = settings_repo.get_erp_config()
        trendyol_cfg = settings_repo.get_trendyol_config()
        general_cfg = settings_repo.get_general_settings()
        self.selected_price_list_id = settings_repo.get_app_setting("selected_trendyol_price_list_id")
        Clock.schedule_once(lambda dt: self.populate_static_settings(erp_cfg, trendyol_cfg, general_cfg))
        Clock.schedule_once(lambda dt: self.test_erp_connection_and_load_lists(None))

    def populate_static_settings(self, erp_cfg, trendyol_cfg, general_cfg):
        self.erp_server_input.text = erp_cfg.get('server') or ''
        self.erp_database_input.text = erp_cfg.get('database') or ''
        self.erp_driver_input.text = erp_cfg.get('driver') or '{ODBC Driver 17 for SQL Server}'
        win_auth = not (erp_cfg.get('username') or erp_cfg.get('password'))
        self.windows_auth_checkbox.active = win_auth
        self.on_windows_auth_changed(None, win_auth)
        self.erp_username_input.text = erp_cfg.get('username') or ''
        self.erp_password_input.text = erp_cfg.get('password') or ''
        self.trendyol_api_key_input.text = trendyol_cfg.get('api_key') or ''
        self.trendyol_api_secret_input.text = trendyol_cfg.get('api_secret') or ''
        self.trendyol_supplier_id_input.text = trendyol_cfg.get('supplier_id') or ''
        self.test_mode_checkbox.active = trendyol_cfg.get('test_mode_enabled', True)
        self.sync_interval_input.text = str(general_cfg.get('sync_interval_minutes') or '15')

    def test_erp_connection_and_load_lists(self, instance):
        erp_config = {
            "server": self.erp_server_input.text,
            "database": self.erp_database_input.text,
            "driver": self.erp_driver_input.text,
            "username": self.erp_username_input.text,
            "password": self.erp_password_input.text
        }
        threading.Thread(target=self._run_erp_test_and_load, args=(erp_config,), daemon=True).start()

    def _run_erp_test_and_load(self, erp_config_override):
        dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
        erp_handler = ERP12Handler(erp_config_override=erp_config_override)
        Clock.schedule_once(lambda dt: dashboard.add_log_message("ERP bağlantısı test ediliyor..."))
        is_success, message = erp_handler.test_connection()
        if not is_success:
            Clock.schedule_once(lambda dt, msg=f"HATA: ERP bağlantısı başarısız! {message}": dashboard.add_log_message(msg))
            return
        Clock.schedule_once(lambda dt: dashboard.add_log_message("ERP Bağlantısı başarılı. Listeler çekiliyor..."))
        self.erp_price_lists_data = erp_handler.get_all_erp_price_lists()
        locations = erp_handler.get_all_erp_locations()
        categories = erp_handler.get_all_erp_categories()
        Clock.schedule_once(lambda dt: self.populate_dynamic_settings(self.erp_price_lists_data, locations, categories))

    def test_api_connection(self, instance):
        api_config = {
            "api_key": self.trendyol_api_key_input.text,
            "api_secret": self.trendyol_api_secret_input.text,
            "supplier_id": self.trendyol_supplier_id_input.text,
            "test_mode_enabled": self.test_mode_checkbox.active
        }
        threading.Thread(target=self._run_api_test, args=(api_config,), daemon=True).start()

    def _run_api_test(self, api_config):
        dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
        Clock.schedule_once(lambda dt: dashboard.add_log_message("Trendyol API bağlantısı test ediliyor..."))
        try:
            api_config['base_url'] = settings_repo.get_trendyol_config().get('base_url')
            api_tester = TrendyolGoAPI(**api_config)
            is_success, message = api_tester.test_connection()
            log_message = f"[color=33cc33]API Testi Başarılı: {message}[/color]" if is_success else f"[color=ff3333]API Testi Başarısız: {message}[/color]"
            Clock.schedule_once(lambda dt, msg=log_message: dashboard.add_log_message(msg))
        except Exception as e:
            log_message = f"[color=ff3333]API Testi sırasında kritik hata: {e}"
            logger.error("API testi sırasında kritik hata oluştu.", exc_info=True)
            Clock.schedule_once(lambda dt, msg=log_message: dashboard.add_log_message(msg))

    def populate_dynamic_settings(self, price_lists, locations, categories):
        if price_lists:
            self.fiyat_listesi_spinner.values = [pl['AD'] for pl in price_lists]
            selected_text = next((pl['AD'] for pl in price_lists if str(pl.get('ID')) == self.selected_price_list_id), None)
            if selected_text:
                self.fiyat_listesi_spinner.text = selected_text
            elif self.fiyat_listesi_spinner.values:
                self.fiyat_listesi_spinner.text = self.fiyat_listesi_spinner.values[0]
        else:
            self.fiyat_listesi_spinner.values = []
            self.fiyat_listesi_spinner.text = SPINNER_PLACEHOLDER_TEXTS[2]

        self.populate_branch_settings_ui(locations)
        self.populate_category_settings_ui(categories)

    def populate_branch_settings_ui(self, locations):
        self.branch_settings_layout.clear_widgets()
        self.branch_setting_widgets.clear()

        header = GridLayout(cols=4, size_hint_y=None, height=dp(35))
        header.add_widget(Label(text="Şube Adı", bold=True))
        header.add_widget(Label(text="Aktif?", bold=True, size_hint_x=0.2))
        header.add_widget(Label(text="Stok Buffer", bold=True, size_hint_x=0.3))
        header.add_widget(Label(text="Trendyol Depo ID", bold=True, size_hint_x=0.4))
        self.branch_settings_layout.add_widget(header)

        branch_map = {str(b['erp_location_id']): b for b in branch_repo.get_all_branch_mappings()}

        for loc in locations:
            row = GridLayout(cols=4, size_hint_y=None, height=dp(40), spacing=dp(5))
            loc_id = str(loc['ID'])
            settings = branch_map.get(loc_id, {})

            chk = CheckBox(active=settings.get('is_active_for_sync', True), size_hint_x=0.2)
            buf = create_styled_textinput(text=str(settings.get('stock_buffer', 0)), size_hint_x=0.3, input_filter='int', halign='center')
            wh_id = create_styled_textinput(text=settings.get('trendyol_warehouse_id', ''), size_hint_x=0.4)

            row.add_widget(Label(text=loc['AD']))
            row.add_widget(chk)
            row.add_widget(buf)
            row.add_widget(wh_id)
            self.branch_settings_layout.add_widget(row)
            self.branch_setting_widgets[loc_id] = {'checkbox': chk, 'buffer': buf, 'warehouse_id': wh_id, 'name': loc['AD']}

    def populate_category_settings_ui(self, categories):
        self.category_settings_layout.clear_widgets()
        self.category_setting_widgets.clear()

        cat_rules = {str(r['erp_category_id']): r for r in category_repo.get_all_category_rules()}

        for cat in categories:
            cat_id = str(cat['ID'])
            rule = cat_rules.get(cat_id, {})

            item_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45), spacing=dp(8))

            cat_label = Label(text=cat['AD'], font_size=dp(13), halign='left', valign='middle', size_hint_x=0.4, shorten=True, ellipsis_options={'color': (1, 0.2, 0.2, 1)})
            cat_label.bind(width=lambda instance, width: setattr(instance, 'text_size', (width, None)))

            controls_group = BoxLayout(spacing=dp(5), size_hint_x=0.6)

            active_layout = BoxLayout(orientation='horizontal', size_hint_x=0.5)
            active_layout.add_widget(Label(text="Aktif?", bold=True, font_size=dp(12), size_hint_x=0.6))
            chk_sync = CheckBox(active=rule.get('sync_enabled', True), size_hint_x=0.4)
            active_layout.add_widget(chk_sync)

            price_layout = BoxLayout(orientation='horizontal', size_hint_x=0.5, spacing=dp(2))
            price_layout.add_widget(Label(text="Fyt %", bold=True, font_size=dp(12), size_hint_x=0.4))
            txt_adj = create_styled_textinput(
                text='{:g}'.format(rule.get('price_adjustment_percentage', 0.0)),
                size_hint_x=0.6, input_filter='float', halign='center'
            )
            price_layout.add_widget(txt_adj)

            controls_group.add_widget(active_layout)
            controls_group.add_widget(price_layout)

            item_row.add_widget(cat_label)
            item_row.add_widget(controls_group)

            self.category_settings_layout.add_widget(item_row)
            self.category_setting_widgets[cat_id] = {'checkbox': chk_sync, 'adjustment': txt_adj, 'name': cat['AD']}

    def on_price_list_selected(self, spinner, text):
        selected_item = next((pl for pl in self.erp_price_lists_data if pl['AD'] == text), None)
        if selected_item:
            self.selected_price_list_id = str(selected_item.get('ID'))

    def save_all_settings(self, instance):
        settings_data = {
            "erp_server": self.erp_server_input.text.strip(),
            "erp_database": self.erp_database_input.text.strip(),
            "erp_driver": self.erp_driver_input.text.strip(),
            "erp_username": "" if self.windows_auth_checkbox.active else self.erp_username_input.text.strip(),
            "erp_password": "" if self.windows_auth_checkbox.active else self.erp_password_input.text.strip(),
            "trendyol_api_key": self.trendyol_api_key_input.text.strip(),
            "trendyol_api_secret": self.trendyol_api_secret_input.text.strip(),
            "trendyol_supplier_id": self.trendyol_supplier_id_input.text.strip(),
            "trendyol_test_mode_enabled": str(self.test_mode_checkbox.active),
            "selected_trendyol_price_list_id": self.selected_price_list_id,
            "sync_interval_minutes": self.sync_interval_input.text.strip() or "15"
        }
        threading.Thread(target=self._run_save_settings, args=(settings_data,), daemon=True).start()

    def _run_save_settings(self, settings_data):
        dashboard = App.get_running_app().root.screen_manager.get_screen('dashboard_screen')
        try:
            for key, value in settings_data.items():
                if value is not None:
                    settings_repo.save_app_setting(key, value)

            for loc_id, widgets in self.branch_setting_widgets.items():
                branch_data = {
                    'erp_location_id': loc_id, 'erp_branch_name': widgets['name'],
                    'is_active': widgets['checkbox'].active,
                    'stock_buffer': int(widgets['buffer'].text or 0),
                    'trendyol_warehouse_id': widgets['warehouse_id'].text.strip(),
                    'erp_price_list_id': self.selected_price_list_id
                }
                branch_repo.add_or_update_branch_mapping(branch_data)

            for cat_id, widgets in self.category_setting_widgets.items():
                rule_data = {
                    'erp_category_id': cat_id, 'erp_category_name': widgets['name'],
                    'sync_enabled': widgets['checkbox'].active,
                    'price_adjustment_percentage': float(widgets['adjustment'].text.replace(',', '.') or 0.0)
                }
                category_repo.add_or_update_category_rule(rule_data)

            Clock.schedule_once(lambda dt: dashboard.add_log_message("Tüm ayarlar başarıyla kaydedildi."))
        except Exception as e:
            logger.error("Ayarlar kaydedilirken hata oluştu.", exc_info=True)
            Clock.schedule_once(lambda dt: dashboard.add_log_message(f"HATA: Ayarlar kaydedilemedi - {e}"))