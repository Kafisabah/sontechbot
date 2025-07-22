# sontechbot/ui/popups/license_activation_popup.py

import logging
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ...core import licensing_handler
from ..helpers import (RENK_BUTON_GRI_ARKA, RENK_BUTON_YESIL_ARKA,
                       RENK_ERROR, RENK_SUCCESS, create_form_row,
                       create_section_header, create_styled_button,
                       create_styled_textinput)

logger = logging.getLogger(__name__)


class LicenseActivationPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "SonTechBot Lisans Aktivasyonu"
        self.size_hint = (0.6, 0.6)
        self.auto_dismiss = False

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        main_layout.add_widget(create_section_header("Lütfen Lisans Bilgilerinizi Girin"))

        form = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, row_default_height=dp(45))
        form.bind(minimum_height=form.setter('height'))

        self.email_input = create_styled_textinput(hint_text="lisans@ornek.com")
        create_form_row(form, "E-posta Adresiniz:", self.email_input)

        self.key_input = create_styled_textinput(hint_text="XXXX-XXXX-XXXX-XXXX")
        create_form_row(form, "Lisans Anahtarınız:", self.key_input)
        main_layout.add_widget(form)

        self.status_label = Label(text="", size_hint_y=None, height=dp(40))
        main_layout.add_widget(self.status_label)

        main_layout.add_widget(Label(size_hint_y=1.0))  # Spacer

        button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        self.activate_button = create_styled_button(
            "Aktive Et", self.activate_license,
            background_color=RENK_BUTON_YESIL_ARKA
        )
        button_layout.add_widget(self.activate_button)
        button_layout.add_widget(
            create_styled_button("Kapat", self.close_app, background_color=RENK_BUTON_GRI_ARKA)
        )
        main_layout.add_widget(button_layout)

        self.content = main_layout

    def close_app(self, instance):
        App.get_running_app().stop()

    def activate_license(self, instance):
        email = self.email_input.text.strip()
        key = self.key_input.text.strip()

        if not email or not key:
            self.update_status("E-posta ve lisans anahtarı boş bırakılamaz.", is_error=True)
            return

        self.activate_button.disabled = True
        self.update_status("Lisans aktive ediliyor, lütfen bekleyin...", is_error=False)
        threading.Thread(target=self._run_activation, args=(email, key), daemon=True).start()

    def _run_activation(self, email, key):
        # Hata burada idi. Artık doğrudan yeni ve doğru olan 'activate_license'
        # fonksiyonunu çağırıyoruz. Bu fonksiyon zaten içinde machine_id'yi alıyor.
        result = licensing_handler.activate_license(email, key)
        
        # Sonucu ana thread'de işlemek için zamanlayıcıyı ayarla
        Clock.schedule_once(lambda dt: self.on_activation_result(result, email, key))
    def on_activation_result(self, result, email=None, key=None):
        self.activate_button.disabled = False
        status = result.get('status')
        message = result.get('message', 'Bilinmeyen bir hata oluştu.')

        if status == 'valid':
            self.update_status("Lisans başarıyla aktive edildi! Program yeniden başlatılacak.", is_error=False)
            licensing_handler.save_license_info(email, key)
            # Programı yeniden başlatmak yerine, kullanıcıya bilgi verip kapatmak daha güvenli olabilir.
            # Veya ana uygulamada bir yeniden başlatma mekanizması kurulabilir.
            # Şimdilik kapatıyoruz.
            Clock.schedule_once(self.close_app, 3)
        else:
            self.update_status(f"Aktivasyon Başarısız: {message}", is_error=True)

    def update_status(self, text, is_error=False):
        self.status_label.text = text
        self.status_label.color = RENK_ERROR if is_error else RENK_SUCCESS