import os

import flet as ft

from gui import theme as t
from gui.paths import SESSION
from gui.settings import LANGUAGES
from gui.views.widgets import PathField, open_folder

LINKS = (("文档", "https://decryptu.github.io/pokeldn/"),
         ("GitHub", "https://github.com/Decryptu/pokeldn"),
         ("Discord", "https://discord.gg/PyvaVYnpXC"))


def keys_found(path: str) -> bool:
    return os.path.isfile(os.path.expanduser(path))


class SettingsView:
    def __init__(self, app):
        self.app = app
        self.keys_state = ft.Container()
        self.column = ft.Column(spacing=12, width=760)
        self.control = ft.ListView([ft.Row([self.column], alignment=ft.MainAxisAlignment.CENTER)],
                                   padding=ft.Padding(4, 8, 4, 24), expand=True)
        self.render()

    def save(self, name: str, value) -> None:
        setattr(self.app.settings, name, value)
        self.app.settings.save()

    def render(self) -> None:
        s = self.app.settings
        home = lambda: os.path.expanduser("~")   # noqa: E731
        keys = PathField(self.app.picker, home, s.keys, "file", ("keys",), self._keys)
        received = PathField(self.app.picker, home, s.received, "dir", on_change=lambda v: self.save("received", v))
        self._keys(s.keys, update=False)
        speed = t.dropdown([("921600", "921600（默认）"), ("1500000", "1500000（更快，需要质量较好的数据线）")],
                           str(s.baud), on_select=lambda e: self.save("baud", int(e.control.value)))

        def number(name, label):
            def store(e):
                try:
                    value = int(e.control.value)
                except ValueError:
                    return
                if 0 <= value <= 65535:
                    self.save(name, value)
            return ft.Column([t.text(label, 11, t.MUTED),
                              t.field(value=str(getattr(s, name)), mono=True, on_change=store)],
                             spacing=4, expand=True)

        trainer = ft.Row([
            ft.Column([t.text("名称", 11, t.MUTED),
                       t.field(value=s.ot, on_change=lambda e: self.save("ot", e.control.value[:12]))],
                      spacing=4, expand=2),
            number("tid", "训练家 ID"),
            number("sid", "里 ID"),
            ft.Column([t.text("语言", 11, t.MUTED),
                       t.dropdown(list(LANGUAGES), str(s.language),
                                  on_select=lambda e: self.save("language", int(e.control.value)))],
                      spacing=4, expand=2),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

        def switch(name, label, help_):
            return t.card(label, None, help_,
                          trailing=t.switch(getattr(s, name), lambda e: self.save(name, e.control.value)))

        def link(label, url):
            return ft.TextButton(label, on_click=lambda e: self.app.page.run_task(self.app.open_url, url),
                                 style=ft.ButtonStyle(color=t.BLUE))

        self.column.controls = [
            t.notch(ft.Row([ft.Icon(ft.Icons.SETTINGS_ROUNDED, size=16, color=t.RED),
                            t.text("设置", 13, weight=ft.FontWeight.W_600)], spacing=8, tight=True)),
            t.card("Switch 密钥", ft.Column([keys.control, self.keys_state], spacing=8),
                   "请使用从您自己的游戏机导出的 prod.keys。它用于解密本地无线广播，且不会离开这台电脑。"),
            t.card("您的训练家", trainer,
                   "此处设置生成宝可梦的初训家。首次启动时会随机生成训练家 ID。"),
            t.card("接收的宝可梦", ft.Row([ft.Container(received.control, expand=True),
                                               t.icon_button(ft.Icons.OPEN_IN_NEW_ROUNDED,
                                                             lambda e: open_folder(os.path.expanduser(s.received)),
                                                             "打开文件夹")]),
                   "游戏机发送来的宝可梦保存在此处。"),
            t.card("串口速度", speed, "连接后电脑与设备之间的通信速度。"),
            switch("capture", "记录每次会话",
                   "保存每次会话的数据报，便于提交问题报告。"),
            switch("board_trace", "记录设备串口通信",
                   "额外保存设备计数器和每条串口消息，仅在排查无线通信问题时使用。"),
            t.card("会话记录", ft.Row([t.button("打开文件夹", lambda e: open_folder(str(SESSION / "captures")),
                                                       ft.Icons.FOLDER_OUTLINED, filled=False)]),
                   "提交问题报告时请附上最新文件。"),
            t.card("关于", ft.Row([link(label, url) for label, url in LINKS], spacing=4),
                   "pokeldn 采用 AGPLv3 许可。宝可梦合法性由 PKHeX.Core（GPLv3）检查。"),
        ]

    def _keys(self, value: str, update: bool = True) -> None:
        self.save("keys", value)
        ok = keys_found(value)
        self.keys_state.content = ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if ok else ft.Icons.ERROR_OUTLINE_ROUNDED, size=15,
                    color=t.GREEN if ok else t.RED),
            t.text("已找到" if ok else "此路径下没有文件", 12, t.GREEN if ok else t.RED)], spacing=6)
        if update:
            self.keys_state.update()
