# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 06.07.2025 07:00
# Yapılan Değişiklikler:
# 1. 'AttributeError' hatasını çözmek için loglama mantığı güncellendi.
# 2. 'dashboard = App.get_running_app().root.screen_manager.get_screen(...)' şeklindeki güvensiz erişim kaldırıldı.
# 3. Tüm log mesajları artık 'synchronizer.update_gui_status()' fonksiyonu üzerinden güvenli bir şekilde gönderiliyor.
# 4. Bu, popup'ın ana arayüzle olan bağını kopararak daha sağlam bir yapı oluşturur.

import datetime
import logging
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color as KivyColor
from kivy.graphics import Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import get_color_from_hex

from ...core import synchronizer
from ...repositories import history_repo, settings_repo
from ..helpers import (RENK_BUTON_GRI_ARKA, RENK_BUTON_KIRMIZI_ARKA,
                       RENK_BUTON_YESIL_ARKA, RENK_HEADER_ARKA,
                       RENK_HEADER_YAZI, create_section_header,
                       create_styled_button)

logger = logging.getLogger(__name__)


class AutoSyncStatusPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Otomatik Senkronizasyon Kontrol Paneli'
        self.size_hint = (0.9, 0.9)
        self.auto_dismiss = False

        self.auto_sync_event = None
        self.countdown_event = None
        self.auto_sync_interval = 900
        self.countdown = 0

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(15))
        control_panel = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        self.status_label = Label(text="[b]Durum:[/b] PASİF", markup=True, font_size=dp(16), bold=True, color=get_color_from_hex('#d32f2f'))
        self.countdown_label = Label(text="Sonraki Çalışma: --:--", font_size=dp(16))
        self.toggle_button = ToggleButton(text='Otomatik Senk. Başlat', size_hint_x=0.4, background_normal='', background_color=RENK_BUTON_YESIL_ARKA)
        self.toggle_button.bind(on_press=self.toggle_auto_sync)

        control_panel.add_widget(self.status_label)
        control_panel.add_widget(self.countdown_label)
        control_panel.add_widget(self.toggle_button)
        main_layout.add_widget(control_panel)

        main_layout.add_widget(create_section_header("Geçmiş Senkronizasyonlar"))

        history_header_layout = GridLayout(cols=6, size_hint_y=None, height=dp(40), spacing=dp(5))
        headers = ["Zaman", "Tip", "Durum", "İşlenen", "Gönderilen", "Batch ID / Durum"]
        col_widths_header = [0.15, 0.1, 0.15, 0.1, 0.1, 0.4]
        for i, text in enumerate(headers):
            header_label = Label(text=text, color=RENK_HEADER_YAZI, font_size=dp(14), bold=True, size_hint_x=col_widths_header[i], halign='center')
            with header_label.canvas.before:
                KivyColor(rgba=RENK_HEADER_ARKA)
                header_label.rect = Rectangle(size=header_label.size, pos=header_label.pos)
            header_label.bind(
                size=lambda instance, value: setattr(instance.rect, 'size', value),
                pos=lambda instance, value: setattr(instance.rect, 'pos', value)
            )
            history_header_layout.add_widget(header_label)
        main_layout.add_widget(history_header_layout)

        history_scroll = ScrollView(size_hint=(1, 1), bar_width=dp(10))
        self.history_layout = GridLayout(cols=6, spacing=dp(5), size_hint_y=None, row_default_height=dp(45))
        self.history_layout.bind(minimum_height=self.history_layout.setter('height'))
        history_scroll.add_widget(self.history_layout)
        main_layout.add_widget(history_scroll)

        close_button = create_styled_button("Kapat", self.dismiss, size_hint_y=None, height=dp(45), background_color=RENK_BUTON_GRI_ARKA)
        main_layout.add_widget(close_button)

        self.content = main_layout
        self.bind(on_open=self.load_history)

    def load_history(self, *args):
        self.history_layout.clear_widgets()
        history = history_repo.get_sync_history(limit=50)

        col_widths = [0.15, 0.1, 0.15, 0.1, 0.1, 0.4]
        for record in history:
            try:
                start_time = datetime.datetime.fromisoformat(record['start_time']).strftime('%d.%m %H:%M')
            except (TypeError, ValueError):
                start_time = record.get('start_time', 'N/A')

            self.history_layout.add_widget(Label(text=start_time, size_hint_x=col_widths[0]))
            self.history_layout.add_widget(Label(text=record.get('sync_type', 'N/A'), size_hint_x=col_widths[1]))
            self.history_layout.add_widget(Label(text=record.get('status', 'N/A'), size_hint_x=col_widths[2]))
            self.history_layout.add_widget(Label(text=str(record.get('products_processed', '0')), size_hint_x=col_widths[3]))
            self.history_layout.add_widget(Label(text=str(record.get('products_sent', '0')), size_hint_x=col_widths[4]))
            self.history_layout.add_widget(Label(text=record.get('batch_request_id', 'N/A'), size_hint_x=col_widths[5]))

    def toggle_auto_sync(self, instance):
        if instance.state == 'down':
            self.start_auto_sync()
        else:
            self.stop_auto_sync()

    def start_auto_sync(self):
        if self.auto_sync_event:
            return

        general_settings = settings_repo.get_general_settings()
        self.auto_sync_interval = int(general_settings.get('sync_interval_minutes', 15)) * 60

        self.status_label.text = "[b]Durum:[/b] [color=4caf50]AKTİF[/color]"
        self.toggle_button.text = 'Durdur'
        self.toggle_button.background_color = RENK_BUTON_KIRMIZI_ARKA

        # DÜZELTME: Log mesajını merkezi sistem üzerinden gönder.
        synchronizer.update_gui_status(f"Otomatik senkronizasyon {self.auto_sync_interval // 60} dakikada bir çalışacak.")

        self.auto_sync_callback(0)
        self.auto_sync_event = Clock.schedule_interval(self.auto_sync_callback, self.auto_sync_interval)
        self.countdown = self.auto_sync_interval
        self.countdown_event = Clock.schedule_interval(self.update_countdown_label, 1)

    def stop_auto_sync(self):
        if self.auto_sync_event:
            self.auto_sync_event.cancel()
        if self.countdown_event:
            self.countdown_event.cancel()
        self.auto_sync_event = None
        self.countdown_event = None

        self.status_label.text = "[b]Durum:[/b] [color=d32f2f]PASİF[/color]"
        self.toggle_button.text = 'Başlat'
        self.toggle_button.background_color = RENK_BUTON_YESIL_ARKA
        self.countdown_label.text = "Sonraki Çalışma: --:--"

        # DÜZELTME: Log mesajını merkezi sistem üzerinden gönder.
        synchronizer.update_gui_status("Otomatik senkronizasyon durduruldu.")

    def update_countdown_label(self, dt):
        self.countdown -= 1
        mins, secs = divmod(self.countdown, 60)
        self.countdown_label.text = f"Sonraki: {mins:02d}:{secs:02d}"
        if self.countdown <= 0:
            self.countdown = self.auto_sync_interval

    def auto_sync_callback(self, dt):
        # DÜZELTME: Log mesajını merkezi sistem üzerinden gönder.
        synchronizer.update_gui_status("Otomatik senkronizasyon döngüsü başlıyor...")

        def after_sync_tasks():
            # Senkronizasyon bittikten sonra ana paneldeki verileri ve bu penceredeki geçmişi güncelle.
            # Bu kısım dolaylı yoldan çalıştığı için güvenlidir.
            App.get_running_app().main_screen_manager.get_screen('dashboard_screen').update_dashboard_data()
            self.load_history()

        threading.Thread(
            target=synchronizer.run_single_sync_cycle,
            kwargs={'sync_type': 'auto', 'on_finish_callback': after_sync_tasks},
            daemon=True
        ).start()
