# sontechbot/ui/popups/update_notification_popup.py

import logging

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ..helpers import (RENK_BUTON_GRI_ARKA, RENK_BUTON_YESIL_ARKA,
                       create_styled_button)

logger = logging.getLogger(__name__)


class UpdateNotificationPopup(Popup):
    def __init__(self, update_info, **kwargs):
        super().__init__(**kwargs)
        self.update_info = update_info
        self.title = f"Yeni Sürüm Mevcut: v{update_info['latest_version']}"
        self.size_hint = (0.7, 0.6)
        self.auto_dismiss = False

        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        main_layout.add_widget(Label(
            text=f"[b]Yeni bir SonTechBot sürümü (v{update_info['latest_version']}) kullanıma hazır![/b]",
            markup=True, font_size=dp(18)
        ))
        
        main_layout.add_widget(Label(
            text="Sürüm Notları:", bold=True, size_hint_y=None, height=dp(30)
        ))
        
        release_notes_label = Label(text=update_info.get('release_notes', 'N/A'))
        main_layout.add_widget(release_notes_label)

        button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        button_layout.add_widget(
            create_styled_button("Daha Sonra Hatırlat", self.dismiss, background_color=RENK_BUTON_GRI_ARKA)
        )
        button_layout.add_widget(
            create_styled_button("Şimdi İndir ve Kur", self.start_update, background_color=RENK_BUTON_YESIL_ARKA)
        )
        main_layout.add_widget(button_layout)
        
        self.content = main_layout

    def start_update(self, instance):
        download_url = self.update_info.get('download_url')
        logger.info(f"Güncelleme başlatılıyor. URL: {download_url}")
        
        # Gerçek indirme ve updater'ı çalıştırma işlemi buraya eklenecek.
        # Şimdilik sadece bir log mesajı ve pencereyi kapatıyoruz.
        from kivy.app import App
        dashboard = App.get_running_app().root.children[0].screen_manager.get_screen('dashboard_screen')
        dashboard.add_log_message("Güncelleme indirme işlemi başlayacak... (Bu özellik yakında tamamlanacak)")
        self.dismiss()