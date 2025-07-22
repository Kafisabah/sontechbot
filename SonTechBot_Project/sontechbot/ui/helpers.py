import logging

from kivy.clock import Clock
from kivy.graphics import Color as KivyColor
from kivy.graphics import Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.snackbar import Snackbar

logger = logging.getLogger(__name__)

RENK_PRIMARY = get_color_from_hex('#00695C')
RENK_PRIMARY_LIGHT = get_color_from_hex('#4DB6AC')
RENK_ACCENT = get_color_from_hex('#FFAB40')
RENK_BACKGROUND = get_color_from_hex('#F5F5F5')
RENK_CARD = get_color_from_hex('#FFFFFF')
RENK_TEXT_PRIMARY = get_color_from_hex('#212121')
RENK_TEXT_SECONDARY = get_color_from_hex('#757575')
RENK_DIVIDER = get_color_from_hex('#BDBDBD')
RENK_SUCCESS = get_color_from_hex('#4CAF50')
RENK_ERROR = get_color_from_hex('#D32F2F')
RENK_WARNING = get_color_from_hex('#FFA000')

RENK_ANA_ARKA_PLAN = RENK_BACKGROUND
RENK_POPUP_ARKA_PLAN = RENK_CARD
RENK_HEADER_ARKA = RENK_PRIMARY
RENK_HEADER_YAZI = get_color_from_hex('#FFFFFF')
RENK_LABEL_NORMAL = RENK_TEXT_SECONDARY
RENK_INPUT_ARKA = get_color_from_hex('#E0E0E0')
RENK_INPUT_YAZI = RENK_TEXT_PRIMARY
RENK_BUTON_MAVI_ARKA = RENK_PRIMARY
RENK_BUTON_YESIL_ARKA = RENK_SUCCESS
RENK_BUTON_GRI_ARKA = RENK_DIVIDER
RENK_BUTON_TURUNCU_ARKA = RENK_ACCENT
RENK_BUTON_KIRMIZI_ARKA = RENK_ERROR
RENK_BUTON_YAZI = get_color_from_hex('#FFFFFF')
RENK_LABEL_AYAR_PASIF_POPUP = RENK_DIVIDER
RENK_YAZI_KOYU = RENK_TEXT_PRIMARY
RENK_LOG_ARKA = get_color_from_hex('#263238')
RENK_LOG_YAZI = get_color_from_hex('#ECEFF1')

SPINNER_PLACEHOLDER_TEXTS = [
    'Fiyat Listesi (Test Et ile Yükle)',
    'Trendyol Fiyat Listesi Seçin', "Liste Yok",
    "Bağlantı Başarısız", "Hata Oluştu"
]


def create_section_header(text):
    header_box = BoxLayout(size_hint_y=None, height=dp(45), padding=(dp(10), dp(5)))
    with header_box.canvas.before:
        KivyColor(rgba=RENK_HEADER_ARKA)
        header_box.rect = Rectangle(size=header_box.size, pos=header_box.pos)
    header_box.bind(
        size=lambda i, v: setattr(i.rect, 'size', v),
        pos=lambda i, v: setattr(i.rect, 'pos', v)
    )
    label = Label(
        text=text, color=RENK_HEADER_YAZI, font_size=dp(18), bold=True,
        halign='left', valign='middle'
    )
    label.bind(texture_size=label.setter('size'))
    header_box.add_widget(label)
    return header_box


def create_styled_textinput(**kwargs):
    text_value = kwargs.pop('text', '')
    if text_value is None:
        text_value = ''
    input_args = {
        'multiline': False, 'font_size': dp(15), 'background_color': RENK_INPUT_ARKA,
        'foreground_color': RENK_INPUT_YAZI, 'size_hint_y': None, 'height': dp(40),
        'padding': [dp(8), dp(8), dp(8), dp(8)]
    }
    input_args.update(kwargs)
    return TextInput(text=str(text_value), **input_args)


def create_styled_button(text, on_press_callback, **kwargs):
    button_args = {
        'text': text,
        'md_bg_color': kwargs.get('background_color', RENK_BUTON_MAVI_ARKA),
        'theme_text_color': "Custom",
        'text_color': RENK_BUTON_YAZI,
        'font_size': dp(15), 'size_hint_y': None, 'height': dp(50)
    }
    kwargs.pop('background_color', None)
    kwargs.pop('background_normal', None)
    kwargs.pop('color', None)

    button_args.update(kwargs)
    button = MDRectangleFlatButton(**button_args)
    if on_press_callback:
        button.bind(on_press=on_press_callback)
    return button


def create_form_row(layout, label_text_widget_or_str, input_widget,
                    label_width_hint=0.35, label_color=RENK_LABEL_NORMAL):
    if isinstance(label_text_widget_or_str, str):
        label = Label(
            text=label_text_widget_or_str, color=label_color,
            font_size=dp(15), halign='right', valign='middle',
            size_hint_x=label_width_hint
        )
    else:
        label = label_text_widget_or_str
        label.size_hint_x = label_width_hint
        label.halign = 'right'
        label.font_size = dp(15)
        label.color = label_color
    label.bind(width=lambda instance, width: setattr(instance, 'text_size', (width * 0.95, None)))
    if not input_widget.size_hint_x:
        input_widget.size_hint_x = 1 - label_width_hint - 0.05
    layout.add_widget(label)
    layout.add_widget(input_widget)


def show_snackbar(text, duration=2.5, bg_color=None):
    from kivy.core.window import Window
    snackbar = Snackbar(text=text, duration=duration)
    if bg_color:
        snackbar.snackbar_x = "10dp"
        snackbar.snackbar_y = "10dp"
        snackbar.size_hint_x = (Window.width - (snackbar.snackbar_x * 2)) / Window.width
        snackbar.bg_color = bg_color
    snackbar.open()


class LoadingPopup(ModalView):
    def __init__(self, message="İşlem devam ediyor...", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.4, 0.2)
        self.background_color = [0, 0, 0, 0.7]
        self.auto_dismiss = False

        main_layout = BoxLayout(
            orientation='vertical', padding=dp(20),
            spacing=dp(10), size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.message_label = Label(
            text=message, font_size=dp(18),
            color=RENK_HEADER_YAZI, halign='center',
            valign='middle'
        )
        main_layout.add_widget(self.message_label)

        self.loading_dots = Label(
            text='.', font_size=dp(30),
            color=RENK_HEADER_YAZI, halign='center',
            valign='middle'
        )
        main_layout.add_widget(self.loading_dots)

        self.add_widget(main_layout)
        self.animation_event = None

    def on_open(self):
        def animate_dots(dt):
            current_text = self.loading_dots.text
            if len(current_text) > 4:
                self.loading_dots.text = '.'
            else:
                self.loading_dots.text += '.'
        self.animation_event = Clock.schedule_interval(animate_dots, 0.5)

    def on_dismiss(self):
        if self.animation_event:
            self.animation_event.cancel()
            self.animation_event = None

    def set_message(self, message):
        self.message_label.text = message