# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 06.07.2025 06:03
# Yapılan Değişiklikler:
# 1. Geliştirme ve test sürecini kolaylaştırmak için "Geliştirici Modu" eklendi.
# 2. config.py dosyasında 'DEV_MODE = True' ayarı varsa, program online lisans kontrolünü atlayarak direkt başlar.
# 3. 'run_license_check' fonksiyonu, DEV_MODE anahtarını kontrol edecek şekilde güncellendi.
# 4. Kod içindeki import yapısı, yeni ayarı okuyabilmek için daha esnek hale getirildi.
# 5. İlgili yerlere geliştirici modu hakkında bilgilendirici log mesajları eklendi.

import logging
import os
import sys
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton

# --- Proje Modüllerini ve Bileşenlerini Import Etme ---
# DÜZELTME: config dosyasını direkt import ederek daha esnek bir yapı sağlıyoruz.
from sontechbot import config
from sontechbot.core import licensing_handler, synchronizer, update_handler
from sontechbot.repositories import (close_database_connection,
                                     initialize_database, settings_repo)
from sontechbot.ui.helpers import (LoadingPopup, RENK_ANA_ARKA_PLAN,
                                   RENK_PRIMARY)
from sontechbot.ui.popups.license_activation_popup import \
    LicenseActivationPopup
from sontechbot.ui.popups.update_notification_popup import \
    UpdateNotificationPopup
from sontechbot.ui.screens.dashboard_screen import DashboardScreen
from sontechbot.ui.screens.reports_screen import ReportsScreen
from sontechbot.ui.screens.settings_screen import SettingsScreen

# --- Loglama Kurulumu ---
def setup_logging():
    """Uygulama genelinde loglama sistemini kurar."""
    if not os.path.exists(config.LOGS_DIR):
        os.makedirs(config.LOGS_DIR)
    
    log_level_str = settings_repo.get_app_setting("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        
        file_handler = RotatingFileHandler(config.LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))

        root_logger.addHandler(stream_handler)
        root_logger.addHandler(file_handler)

    logging.info(f"--- {config.APP_TITLE} v{config.APP_VERSION} başlatıldı ---")
# --- Loglama Kurulumu Sonu ---


# --- Kenar Çubuğu (Sidebar) Arayüz Sınıfı ---
class Sidebar(MDBoxLayout):
    """Uygulamanın sol tarafında bulunan ve ekranlar arası geçişi sağlayan menü."""
    def __init__(self, screen_manager, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager
        self.orientation = 'vertical'
        self.size_hint_x = None
        self.width = dp(220)
        self.padding = dp(10)
        self.spacing = dp(15)
        self.md_bg_color = RENK_PRIMARY

        self.add_widget(Label(text=config.APP_TITLE.split(" ")[0], font_size=dp(24), bold=True, size_hint_y=None, height=dp(50)))
        self.add_widget(Label(text=f"v{config.APP_VERSION}", font_size=dp(12), color=(0.9, 0.9, 0.9, 1), size_hint_y=None, height=dp(20)))
        self.add_menu_button("Ana Panel", "view-dashboard", "dashboard_screen")
        self.add_menu_button("Ayarlar", "cog", "settings_screen")
        self.add_menu_button("Raporlar", "chart-bar", "reports_screen")
        self.add_widget(Label(size_hint_y=1))

    def add_menu_button(self, text, icon_name, screen_name):
        button = MDRaisedButton(
            text=text, icon=icon_name, on_release=lambda x: self.change_screen(screen_name, text),
            size_hint_x=1, elevation=1
        )
        self.add_widget(button)

    def change_screen(self, screen_name, button_text):
        for child in self.children:
            if isinstance(child, MDRaisedButton):
                child.md_bg_color = App.get_running_app().theme_cls.primary_light if child.text == button_text else App.get_running_app().theme_cls.primary_color
        self.screen_manager.current = screen_name
        logger.info(f"Ekran değiştirildi: {screen_name}")
# --- Kenar Çubuğu Sınıfı Sonu ---


# --- Ana Pencere İskeleti ---
class RootWidget(BoxLayout):
    """Uygulamanın ana iskeleti. Kenar çubuğunu ve ekran alanını birleştirir."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.screen_manager = ScreenManager(size_hint_x=1)
        self.sidebar = Sidebar(screen_manager=self.screen_manager)
        
        self.screen_manager.add_widget(DashboardScreen(name='dashboard_screen'))
        self.screen_manager.add_widget(SettingsScreen(name='settings_screen'))
        self.screen_manager.add_widget(ReportsScreen(name='reports_screen'))
        
        self.add_widget(self.sidebar)
        self.add_widget(self.screen_manager)
# --- Ana Pencere İskeleti Sonu ---


# --- Ana Uygulama Sınıfı (GÜNCELLEME KONTROLÜ İLE) ---
class SonTechBotGUIApp(MDApp):
    """Projenin ana uygulama sınıfı. Tüm başlangıç mantığını ve olay yönetimini içerir."""

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Orange"
        self.theme_cls.theme_style = "Light"
        Window.clearcolor = RENK_ANA_ARKA_PLAN
        self.title = "SonTechBot - Başlatılıyor..."
        
        self.loading_popup = LoadingPopup(message="Lisans durumu kontrol ediliyor...")
        self.loading_popup.open()
        
        threading.Thread(target=self.run_license_check, daemon=True).start()
        return BoxLayout()

    def run_license_check(self):
        """Lisans kontrolünü yapar veya Geliştirici Modu aktifse atlar."""
        try:
            initialize_database()
            setup_logging()
            
            # --- YENİ: GELİŞTİRİCİ MODU KONTROLÜ ---
            # config.py dosyasındaki DEV_MODE True ise, lisans kontrolünü atla.
            if getattr(config, 'DEV_MODE', False):
                logger.warning("!!! GELİŞTİRİCİ MODU AKTİF: Lisans kontrolü atlandı. !!!")
                license_result = {'status': 'valid', 'message': 'Geliştirici modu aktif.'}
            else:
                # Normal lisans kontrolü
                logger.info("Lisans kontrolü yapılıyor...")
                license_result = licensing_handler.check_license_status()
            
            Clock.schedule_once(lambda dt: self.on_license_check_complete(license_result))
        except Exception as e:
            logger.critical("Başlangıç kontrolleri sırasında kritik hata!", exc_info=True)
            Clock.schedule_once(lambda dt: self.show_fatal_error_popup(str(e)))

    def on_license_check_complete(self, result):
        """Lisans kontrolü bittiğinde çağrılır ve sonuca göre davranır."""
        self.loading_popup.dismiss()
        status = result.get('status')
        
        if status in ['valid', 'trial', 'ACTIVE', 'offline']:
            self.initialize_main_app(result)
            threading.Thread(target=self.run_update_check, daemon=True).start()
        else:
            message = result.get('message', 'Bilinmeyen bir hata.')
            logger.warning(f"Aktivasyon gerekli. Sebep: {status} - Mesaj: {message}")
            LicenseActivationPopup().open()

    def run_update_check(self):
        """Güncelleme kontrolünü arka planda çalıştırır."""
        update_result = update_handler.check_for_updates()
        if update_result.get('update_available'):
            Clock.schedule_once(lambda dt: UpdateNotificationPopup(update_info=update_result).open())

    def initialize_main_app(self, license_result):
        """Tüm kontrollerden sonra ana uygulama arayüzünü oluşturur ve gösterir."""
        self.title = f'{config.APP_TITLE} v{config.APP_VERSION}'
        if license_result.get('status') == 'trial':
            self.title += f" (Deneme Sürümü - Kalan {license_result.get('days_left', 'N/A')} gün)"
        
        root = RootWidget()
        self.root.clear_widgets()
        self.root.add_widget(root)
        
        dashboard = root.screen_manager.get_screen('dashboard_screen')
        synchronizer.set_gui_status_updater(dashboard.add_log_message)
        
        Window.bind(on_keyboard=self.on_key)
        logger.info(f"Uygulama arayüzü başarıyla başlatıldı. Lisans Durumu: {license_result.get('status')}")
        root.sidebar.change_screen('dashboard_screen', 'Ana Panel')

    def show_fatal_error_popup(self, message):
        """Kurtarılamaz bir hata durumunda kullanıcıya bilgi verip programı kapatır."""
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text=f"Kritik Hata:\n\n{message}\n\nUygulama kapatılacak.", halign="center"))
        btn = MDRaisedButton(text="Kapat", on_release=self.stop, pos_hint={'center_x': 0.5})
        content.add_widget(btn)
        popup = Popup(title="Kritik Hata", content=content, size_hint=(0.5, 0.4), auto_dismiss=False)
        popup.open()
        
    def on_stop(self):
        """Uygulama kapatılırken çalışan son fonksiyondur."""
        logger.info("Uygulama kapatılıyor...")
        close_database_connection()
        logger.info("Veritabanı bağlantısı kapatıldı. Çıkış yapıldı.")

    def on_key(self, window, key, scancode, codepoint, modifier):
        """Klavye tuş basımlarını yakalar."""
        if not self.root.children or not isinstance(self.root.children[0], RootWidget): return False
        if key == 27:
            sm = self.root.children[0].screen_manager
            if sm.current != 'dashboard_screen':
                self.root.children[0].sidebar.change_screen('dashboard_screen', 'Ana Panel')
                return True
            else:
                current_time = time.time()
                if not hasattr(self, 'last_esc_press_time') or (current_time - self.last_esc_press_time) > 2:
                    self.last_esc_press_time = current_time
                    dashboard = sm.get_screen('dashboard_screen')
                    dashboard.add_log_message("Çıkmak için ESC tuşuna tekrar basın.")
                else:
                    self.show_exit_popup()
                return True
        return False

    def show_exit_popup(self):
        """Çıkış onayı penceresini gösterir."""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text='Programdan çıkmak istediğinize emin misiniz?'))
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        popup = Popup(title='Çıkış Onayı', content=content, size_hint=(0.4, 0.3), auto_dismiss=True)
        yes_button = MDRaisedButton(text="Evet, Çık", on_release=self.stop)
        no_button = MDRaisedButton(text="Hayır", on_release=popup.dismiss)
        buttons_layout.add_widget(yes_button)
        buttons_layout.add_widget(no_button)
        content.add_widget(buttons_layout)
        popup.open()


# --- Programın Ana Giriş Noktası ---
if __name__ == '__main__':
    try:
        SonTechBotGUIApp().run()
    except Exception as e:
        logger.critical("Uygulama beklenmedik bir hata ile çöktü!", exc_info=True)
