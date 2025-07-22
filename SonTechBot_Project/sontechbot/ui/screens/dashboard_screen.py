# -*- coding: utf-8 -*-
# Güncelleme Tarihi: 06.07.2025 06:50
# Yapılan Değişiklikler:
# 1. 'AttributeError' hatasını çözmek için ekran değiştirme mantığı güncellendi.
# 2. Ekran değiştirme komutu, artık 'App.get_running_app().main_screen_manager' üzerinden,
#    ana uygulamada oluşturulan merkezi ve güvenli referansı kullanıyor.

import datetime
import logging
import random
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy_garden.graph import BarPlot, Graph
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from sontechbot.core import synchronizer
from sontechbot.repositories import dashboard_repo
from sontechbot.ui.helpers import (RENK_BUTON_TURUNCU_ARKA,
                                   RENK_BUTON_YESIL_ARKA, RENK_CARD, RENK_ERROR,
                                   RENK_LOG_ARKA, RENK_LOG_YAZI, RENK_PRIMARY,
                                   RENK_SUCCESS, RENK_TEXT_SECONDARY,
                                   RENK_WARNING, create_styled_button)
from sontechbot.ui.popups.auto_sync_status_popup import AutoSyncStatusPopup

logger = logging.getLogger(__name__)


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.auto_sync_popup = None
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))

        top_panel_layout = BoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=0.6)
        kpi_layout = GridLayout(cols=1, spacing=dp(20), size_hint_x=0.4)

        self.health_score_card = self._create_kpi_card("Sağlık Skoru (24s)", "100%")
        self.total_issues_card = self._create_kpi_card("Çözülmemiş Sorunlar", "0")
        self.last_sync_card = self._create_kpi_card("Son Senkronizasyon", "N/A")

        kpi_layout.add_widget(self.health_score_card)
        kpi_layout.add_widget(self.total_issues_card)
        kpi_layout.add_widget(self.last_sync_card)

        graph_card = MDCard(
            orientation='vertical', padding=dp(15), size_hint=(0.6, 1),
            md_bg_color=RENK_CARD, elevation=2, shadow_softness=2,
            radius=[15, 15, 15, 15]
        )
        graph_card.add_widget(MDLabel(text="Sorun Dağılımı", halign='center', theme_text_color="Primary", font_style="H6"))
        self.issue_graph = self._create_issue_graph()
        graph_card.add_widget(self.issue_graph)

        top_panel_layout.add_widget(kpi_layout)
        top_panel_layout.add_widget(graph_card)
        main_layout.add_widget(top_panel_layout)

        button_layout = GridLayout(cols=3, size_hint_y=None, height=dp(50), spacing=dp(15))
        button_layout.add_widget(create_styled_button('Manuel Senkronizasyon', self.start_manual_sync, icon="sync"))
        button_layout.add_widget(create_styled_button('Raporları Görüntüle', self.go_to_reports_screen, background_color=RENK_BUTON_TURUNCU_ARKA, icon="file-chart"))
        button_layout.add_widget(create_styled_button('Otomatik Senk. Paneli', self.show_auto_sync_popup, background_color=RENK_BUTON_YESIL_ARKA, icon="camera-timer"))
        main_layout.add_widget(button_layout)

        log_card = MDCard(
            orientation='vertical', padding=(dp(10), dp(5), dp(10), dp(10)),
            md_bg_color=RENK_LOG_ARKA, size_hint=(1, 1), radius=[15, 15, 15, 15]
        )
        log_card.add_widget(MDLabel(text="İşlem Logları", theme_text_color="Custom", text_color=RENK_LOG_YAZI, font_style="H6", size_hint_y=None, height=dp(30)))

        self.log_scroll = ScrollView(bar_width=dp(10))
        self.log_label = MDLabel(text='[b]Durum:[/b] Beklemede...\n', markup=True, theme_text_color="Custom", text_color=RENK_LOG_YAZI, size_hint_y=None)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.log_scroll.add_widget(self.log_label)
        log_card.add_widget(self.log_scroll)

        main_layout.add_widget(log_card)
        self.add_widget(main_layout)

    def on_enter(self, *args):
        self.update_dashboard_data()

    def _create_kpi_card(self, title, initial_value):
        card = MDCard(
            orientation='vertical', padding=dp(20), size_hint=(1, 1),
            md_bg_color=RENK_CARD, elevation=2, shadow_softness=2,
            radius=[15, 15, 15, 15]
        )
        title_label = MDLabel(text=title, halign='center', theme_text_color="Secondary", font_style="H6")
        value_label = MDLabel(text=initial_value, halign='center', theme_text_color="Primary", font_style="H3", bold=True)
        card.add_widget(title_label)
        card.add_widget(value_label)
        card.value_label = value_label
        return card

    def _create_issue_graph(self):
        graph = Graph(
            x_ticks_minor=0, x_ticks_major=1, y_ticks_major=5, y_ticks_minor=0,
            xmin=0, xmax=10, ymin=0, ymax=50, padding=dp(10),
            border_color=[0, 0, 0, 0],
            label_options={'color': RENK_TEXT_SECONDARY, 'bold': True}
        )
        return graph

    def update_dashboard_data(self):
        threading.Thread(target=self._run_update_dashboard, daemon=True).start()

    def _run_update_dashboard(self):
        stats = dashboard_repo.get_dashboard_stats()
        Clock.schedule_once(lambda dt: self.populate_dashboard(stats))

    def populate_dashboard(self, stats):
        health_score = stats.get('health_score', 0)
        self.health_score_card.value_label.text = f"{health_score}%"
        if health_score >= 95:
            self.health_score_card.value_label.text_color = RENK_SUCCESS
        elif health_score >= 80:
            self.health_score_card.value_label.text_color = RENK_WARNING
        else:
            self.health_score_card.value_label.text_color = RENK_ERROR

        self.total_issues_card.value_label.text = str(stats.get("total_unresolved_issues", 0))

        for widget in list(self.last_sync_card.children):
            if isinstance(widget, MDLabel) and widget.font_style != "H6":
                self.last_sync_card.remove_widget(widget)

        self.last_sync_card.value_label.text = f"{stats.get('last_sync_duration', 'N/A')}"
        self.last_sync_card.value_label.font_style = "H5"
        self.last_sync_card.add_widget(MDLabel(text=stats.get("last_sync_summary", "Veri Yok"), halign='center', theme_text_color="Secondary", adaptive_height=True))

        for plot in self.issue_graph.plots:
            self.issue_graph.remove_plot(plot)

        issue_counts = stats.get('issue_counts', {})
        if not issue_counts:
            self.issue_graph.xmax = 1
            self.issue_graph.ymax = 10
            return

        self.issue_graph.xmax = len(issue_counts)
        max_count = max(issue_counts.values()) if issue_counts else 10
        self.issue_graph.ymax = max(10, max_count + (max_count * 0.2))
        self.issue_graph.y_ticks_major = max(1, int(self.issue_graph.ymax / 5))

        plot = BarPlot(color=RENK_PRIMARY, bar_width=dp(30))
        plot.points = [(i + 0.5, count) for i, count in enumerate(issue_counts.values())]
        self.issue_graph.add_plot(plot)
        self.issue_graph.x_labels = [label.replace("_", " ").title() for label in issue_counts.keys()]

    def add_log_message(self, message):
        def update_label(dt):
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            if "HATA:" in message.upper() or "KRİTİK" in message.upper():
                color_hex_str = 'D32F2F'
            elif "UYARI:" in message.upper():
                color_hex_str = 'FFA000'
            elif "BAŞARILI" in message.upper():
                color_hex_str = '4CAF50'
            else:
                color_hex_str = 'ECEFF1'
            colored_message = f"[color={color_hex_str}]{message}[/color]"
            self.log_label.text += f"[color=808080]{timestamp}[/color] - {colored_message}\n"
            self.log_scroll.scroll_y = 0
        Clock.schedule_once(update_label)

    def start_manual_sync(self, instance):
        self.add_log_message("Manuel senkronizasyon talebi alındı, başlatılıyor...")
        threading.Thread(target=self._run_sync_and_refresh, daemon=True).start()

    def _run_sync_and_refresh(self):
        synchronizer.run_single_sync_cycle(sync_type='manual', on_finish_callback=self.update_dashboard_data)

    def go_to_reports_screen(self, instance):
        # DÜZELTME: Ekran yöneticisine ana uygulamadaki merkezi referans üzerinden eriş.
        App.get_running_app().main_screen_manager.current = 'reports_screen'

    def show_auto_sync_popup(self, instance):
        if not self.auto_sync_popup:
            self.auto_sync_popup = AutoSyncStatusPopup()
        self.auto_sync_popup.load_history()
        self.auto_sync_popup.open()
