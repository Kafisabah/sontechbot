import json
import logging

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex

from ..helpers import (RENK_BUTON_GRI_ARKA, RENK_HEADER_ARKA,
                       RENK_HEADER_YAZI, create_styled_button)

logger = logging.getLogger(__name__)


class ErrorDetailPopup(Popup):
    def __init__(self, issue_data, **kwargs):
        super().__init__(**kwargs)
        self.title = "Hata Detayları"
        self.title_color = RENK_HEADER_YAZI
        self.size_hint = (0.8, 0.7)
        self.auto_dismiss = False
        self.background_color = get_color_from_hex('#37474FDD')
        self.separator_color = RENK_HEADER_ARKA

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll_view = ScrollView(bar_width=dp(10))
        content_layout = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        content_layout.bind(minimum_height=content_layout.setter('height'))

        def add_detail_row(key, value):
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
            key_label = Label(
                text=f"[b]{key}:[/b]", markup=True, halign='right',
                size_hint_x=0.3, color=RENK_HEADER_YAZI, font_size=dp(14)
            )
            value_label = Label(
                text=str(value), halign='left', valign='top',
                size_hint_x=0.7, color=RENK_HEADER_YAZI, font_size=dp(14)
            )
            value_label.bind(width=lambda instance, width: setattr(instance, 'text_size', (width * 0.95, None)))
            box.add_widget(key_label)
            box.add_widget(value_label)
            content_layout.add_widget(box)

        add_detail_row("ID", issue_data.get('id', 'N/A'))
        add_detail_row("Zaman Damgası", issue_data.get('timestamp', 'N/A'))
        add_detail_row("Ürün ID (ERP)", issue_data.get('erp_product_id', 'N/A'))
        add_detail_row("Barkod", issue_data.get('barcode', 'N/A'))
        add_detail_row("Şube Adı", issue_data.get('erp_branch_name', 'N/A'))
        add_detail_row("Sorun Tipi", issue_data.get('issue_type', 'N/A'))
        add_detail_row("Mesaj", issue_data.get('message', 'N/A'))
        add_detail_row("Çözüldü", "Evet" if issue_data.get('is_resolved') else "Hayır")

        try:
            details_str = issue_data.get('details_json')
            details = json.loads(details_str) if details_str else {}
        except (json.JSONDecodeError, TypeError):
            details = {"raw_details": details_str}

        if details:
            header_label = Label(
                text="[b]Ek Detaylar (JSON):[/b]", markup=True, size_hint_y=None,
                height=dp(30), font_size=dp(16), color=RENK_HEADER_YAZI
            )
            content_layout.add_widget(header_label)
            for key, value in details.items():
                display_value = json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                add_detail_row(key, display_value)

        scroll_view.add_widget(content_layout)
        main_layout.add_widget(scroll_view)

        close_button = create_styled_button(
            "Kapat", self.dismiss, size_hint_y=None, height=dp(45),
            background_color=RENK_BUTON_GRI_ARKA
        )
        main_layout.add_widget(close_button)
        self.content = main_layout