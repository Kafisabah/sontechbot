# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 08.07.2025 05:35
# Yapılan Değişiklikler:
# 1. Bu dosya, projenin tüm özelliklerini içeren son, tam ve kararlı sürümüdür.
# 2. Sistem tepsisi, otomatik başlatma, pasif lisanslama ve otomatik ODBC sürücüsü algılama özellikleri entegre edilmiştir.
# 3. Tüm bilinen hatalar ('AttributeError', 'KeyError', 'NameError', 'TypeError') düzeltilmiştir.
# 4. Kodun her bölümüne, ne işe yaradığını açıklayan detaylı Türkçe yorumlar eklenmiştir.

import os
import sys

# Kivy'nin '--dev' gibi özel komutlarımızı engellememesi için bu satır,
# Kivy veya KivyMD ile ilgili herhangi bir import'tan ÖNCE gelmelidir.
os.environ['KIVY_NO_ARGS'] = '1'

# Diğer importlar bu satırdan sonra gelmelidir.
import logging
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler

# Gerekli Windows ve Arayüz Kütüphaneleri
import ctypes
import winshell
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
from PIL import Image, ImageDraw
from pystray import Icon as TrayIcon
from pystray import Menu as TrayMenu
from pystray import MenuItem as TrayMenuItem

# --- Proje İçi Modüller ---
from sontechbot import config
from sontechbot.core import licensing_handler, synchronizer
from sontechbot.repositories import (close_database_connection,
                                     initialize_database, settings_repo)
from sontechbot.ui.helpers import (LoadingPopup, RENK_ANA_ARKA_PLAN,
                                   RENK_PRIMARY)
from sontechbot.ui.popups.license_activation_popup import \
    LicenseActivationPopup
from sontechbot.ui.screens.dashboard_screen import DashboardScreen
from sontechbot.ui.screens.reports_screen import ReportsScreen
from sontechbot.ui.screens.settings_screen import SettingsScreen

# --- Loglama Kurulumu ---
# Programın her yerinden erişilebilmesi için loglama kurulumu global olarak yapılır.
if not os.path.exists(config.LOGS_DIR):
    os.makedirs(config.LOGS_DIR)

log_level = getattr(logging, settings_repo.get_app_setting("log_level", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format=config.LOG_FORMAT,
    handlers=[
        RotatingFileHandler(config.LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Yardımcı Fonksiyonlar ---
def create_tray_image():
    """Sistem tepsisi için programatik olarak 64x64 piksel bir ikon oluşturur."""
    width, height = 64, 64
    image = Image.new('RGB', (width, height), 'white')
    dc = ImageDraw.Draw(image)
    # Basit bir "S" harfi benzeri logo çizimi
    dc.rectangle((width // 2, 0, width, height // 2), fill='#00695C')
    dc.rectangle((0, height // 2, width // 2, height), fill='#00695C')
    return image

def create_startup_shortcut():
    """Programın, bilgisayar her açıldığında otomatik başlaması için Başlangıç klasörüne bir kısayol oluşturur."""
    startup_folder = winshell.startup()
    shortcut_path = os.path.join(startup_folder, f"{config.APP_NAME}.lnk")
    
    # Eğer kısayol zaten mevcut değilse oluştur
    if not os.path.exists(shortcut_path):
        target_path = sys.executable
        logger.info(f"Başlangıç kısayolu oluşturuluyor: {shortcut_path}")
        try:
            winshell.CreateShortcut(
                Path=shortcut_path, Target=target_path,
                Icon=(target_path, 0), Description=config.APP_TITLE
            )
            logger.info("Başlangıç kısayolu başarıyla oluşturuldu.")
        except Exception as e:
            logger.error(f"Başlangıç kısayolu oluşturulamadı: {e}")

# --- Ana Arayüz Sınıfları ---
class Sidebar(MDBoxLayout):
    """Uygulamanın sol tarafındaki menü çubuğu."""
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
        button = MDRaisedButton(text=text, icon=icon_name, on_release=lambda x: self.change_screen(screen_name, text), size_hint_x=1, elevation=1)
        self.add_widget(button)

    def change_screen(self, screen_name, button_text):
        for child in self.children:
            if isinstance(child, MDRaisedButton):
                child.md_bg_color = App.get_running_app().theme_cls.primary_light if child.text == button_text else App.get_running_app().theme_cls.primary_color
        App.get_running_app().main_screen_manager.current = screen_name

class RootWidget(BoxLayout):
    """Kenar çubuğu ile ana ekran alanını birleştiren ana pencere iskeleti."""
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

# --- Ana Uygulama Sınıfı ---
class SonTechBotGUIApp(MDApp):
    """Projenin ana uygulama sınıfı. Tüm mantığı yönetir."""
    
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Orange"
        self.theme_cls.theme_style = "Light"
        Window.clearcolor = RENK_ANA_ARKA_PLAN
        self.title = "SonTechBot - Başlatılıyor..."
        self.tray_icon = None
        self.main_screen_manager = None
        Window.bind(on_request_close=self.on_request_close)
        return BoxLayout()

    def on_start(self):
        """Uygulama başladığında çalışır."""
        threading.Thread(target=self.run_startup_checks, daemon=True).start()

    def run_startup_checks(self):
        """Başlangıç işlemlerini (veritabanı, kısayol, lisans) yapar."""
        try:
            logger.info(f"--- {config.APP_TITLE} v{config.APP_VERSION} başlatılıyor ---")
            initialize_database()
            create_startup_shortcut()
            license_result = licensing_handler.check_license_status()
            Clock.schedule_once(lambda dt: self.on_license_check_complete(license_result))
        except Exception as e:
            logger.critical(f"Başlangıç sırasında kritik hata: {e}", exc_info=True)

    def on_license_check_complete(self, result):
        """Lisans kontrolü sonucuna göre ana arayüzü başlatır veya aktivasyon ister."""
        if result.get('status') == 'valid':
            self.initialize_main_app()
        else:
            logger.warning(f"Aktivasyon gerekli: {result.get('message')}")
            LicenseActivationPopup().open()

    def initialize_main_app(self, *args):
        """Ana uygulama arayüzünü kurar ve gösterir."""
        self.title = f'{config.APP_TITLE} v{config.APP_VERSION}'
        root = RootWidget()
        self.main_screen_manager = root.screen_manager
        self.root.clear_widgets()
        self.root.add_widget(root)
        
        dashboard = self.main_screen_manager.get_screen('dashboard_screen')
        synchronizer.set_gui_status_updater(dashboard.add_log_message)
        
        logger.info("Uygulama arayüzü başarıyla başlatıldı.")
        root.sidebar.change_screen('dashboard_screen', 'Ana Panel')
        
        threading.Thread(target=self.setup_tray_icon, daemon=True).start()
        
        # İlk senkronizasyonun başlaması
        logger.info("İlk otomatik senkronizasyon döngüsü başlatılıyor...")
        dashboard.start_manual_sync(None)

    def setup_tray_icon(self):
        """Sistem tepsisi ikonunu ve menüsünü oluşturup çalıştırır."""
        image = create_tray_image()
        menu = TrayMenu(
            TrayMenuItem('Göster', self.show_window, default=True),
            TrayMenuItem('Çıkış', self.exit_app)
        )
        self.tray_icon = TrayIcon(config.APP_NAME, image, self.title, menu)
        self.tray_icon.run()

    def show_window(self, *args):
        """Gizlenmiş pencereyi tekrar görünür yapar ve öne getirir."""
        Window.show()
        try:
            ctypes.windll.user32.SetForegroundWindowW(Window._hwnd)
        except Exception as e:
            logger.warning(f"Pencere öne getirilemedi: {e}")

    def on_request_close(self, *args, **kwargs):
        """Pencere üzerindeki 'X' butonuna basıldığında çalışır."""
        if self.tray_icon and self.tray_icon.visible:
            Window.hide()
            self.tray_icon.notify("Program arka planda çalışmaya devam ediyor.", config.APP_TITLE)
            return True  # Kivy'nin programı kapatmasını engelle
        else:
            self.stop()
            return False

    def exit_app(self, *args):
        """Sistem tepsisindeki 'Çıkış' menüsünden programı tamamen kapatır."""
        logger.info("Sistem tepsisinden çıkış yapılıyor...")
        if self.tray_icon:
            self.tray_icon.stop()
        
        Clock.schedule_once(self.stop, 0.1)

    def on_stop(self):
        """Uygulama kapatılırken çalışan son fonksiyondur."""
        logger.info("Uygulama kapatılıyor...")
        close_database_connection()
        logger.info("Veritabanı bağlantısı kapatıldı. Çıkış yapıldı.")

# --- Programın Ana Giriş Noktası ---
if __name__ == '__main__':
    try:
        SonTechBotGUIApp().run()
    except Exception as e:
        logger.critical("Uygulama beklenmedik bir hata ile çöktü!", exc_info=True)
