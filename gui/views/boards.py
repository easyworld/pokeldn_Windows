import os
import re
import threading
import time

import flet as ft
import serial

from gui import board, runner
from gui.paths import SESSION
from gui import theme as t
from gui.views.widgets import Log

PERCENT = re.compile(r"(\d{1,3}(?:\.\d)?)\s?%")

FLASH_STEPS = [
    "使用 USB 数据线。仅支持充电的线能供电，但不会显示串口。",
    "在左侧选择设备。",
    "点击刷写。如果一直显示“正在连接”，按住 BOOT 键直到开始写入。",
    "完成后蓝色指示灯会闪烁一次，然后缓慢呼吸。",
]


class BoardView:
    def __init__(self, app):
        self.app = app
        self.ports: list[board.Port] = []
        self.selected: str = ""
        self.identities: dict[str, board.Identity | str] = {}   # device -> identity or error
        self.visible = False
        self.list = ft.ListView(spacing=4, padding=8, expand=True)
        self.detail = ft.Column(spacing=12)
        self.log = Log(app.page, "设备识别与固件刷写输出会显示在这里。")
        self.progress = ft.ProgressBar(value=0, color=t.BLUE, bgcolor=t.FIELD, border_radius=4, visible=False)
        self.progress_text = t.text("", 12, t.MUTED)
        self.control = ft.Row([
            t.panel(ft.Column([
                t.panel_header("设备", t.icon_button(ft.Icons.REFRESH_ROUNDED, lambda e: self.scan(), "重新扫描")),
                self.list,
            ], spacing=0, expand=True), width=270),
            ft.ListView([self.detail], padding=ft.Padding(4, 0, 4, 24), expand=True),
            t.panel(ft.Column([t.panel_header("活动日志"),
                               ft.Container(self.log.control, padding=14, expand=True)],
                              spacing=0, expand=True), width=380),
        ], spacing=14, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    # Port list, polled while the page is open so a board shows up when it is plugged in

    def enter(self, **_) -> None:
        self.scan(update=False)
        if not self.visible:
            self.visible = True
            threading.Thread(target=self._poll, daemon=True).start()

    def leave(self) -> None:
        self.visible = False

    def _poll(self) -> None:
        while self.visible:
            time.sleep(2)
            if self.visible and [p.device for p in board.ports()] != [p.device for p in self.ports]:
                self.app.ui(self.scan)

    def scan(self, update: bool = True) -> None:
        self.ports = board.ports()
        devices = [p.device for p in self.ports]
        if self.selected not in devices:
            self.selected = self.app.radio_port() or (devices[0] if devices else "")
        self.render()
        if update:
            self.control.update()

    def port(self) -> board.Port | None:
        return next((p for p in self.ports if p.device == self.selected), None)

    def name_of(self, device: str) -> str:
        ident = self.identities.get(device)
        if isinstance(ident, board.Identity):
            return self.app.settings.board_names.get(ident.sta_mac, "")
        return ""

    def render(self) -> None:
        rows = []
        for p in self.ports:
            active = p.device == self.selected
            radio = p.device == self.app.settings.radio_port
            rows.append(ft.Container(ft.Row([
                ft.Icon(ft.Icons.MEMORY_ROUNDED, size=18, color=t.BLUE if active else t.FAINT),
                ft.Column([
                    t.text(self.name_of(p.device) or os.path.basename(p.device), 13,
                           t.TEXT if active else "#C5C7CD", weight=ft.FontWeight.W_600),
                    t.text(p.bridge, 11, t.MUTED),
                ], spacing=1, expand=True),
                t.pill("无线设备", t.RED) if radio else ft.Container(),
            ], spacing=10), padding=ft.Padding(10, 8, 10, 8), border_radius=9,
                bgcolor=t.HOVER if active else None,
                on_click=lambda e, d=p.device: self._select(d)))
        if not rows:
            rows.append(ft.Container(ft.Column([
                ft.Icon(ft.Icons.USB_OFF_ROUNDED, size=28, color=t.FAINT),
                t.text("未找到设备", 13, t.MUTED, weight=ft.FontWeight.W_600),
                t.text("请用数据线连接设备，连接后会自动显示在这里。", 12, t.FAINT,
                       text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6), padding=24))
        self.list.controls = rows
        self.detail.controls = [self.board_card(), self.flash_card(), self.help_card()]

    def _select(self, device: str) -> None:
        self.selected = device
        self.render()
        self.control.update()

    # The selected board

    def board_card(self) -> ft.Control:
        p = self.port()
        if not p:
            return t.card("未选择设备", None, "连接设备后可在左侧选择。")
        ident = self.identities.get(p.device)
        if isinstance(ident, board.Identity):
            firmware = (t.pill("pokeldn 固件", t.GREEN) if ident.current else
                        t.pill(f"固件过旧（协议 {ident.protocol}），请刷写", t.RED))
            mac = ident.sta_mac
        elif isinstance(ident, str):
            firmware, mac = t.pill(ident, t.RED), "未知"
        else:
            firmware, mac = t.pill("尚未检查", t.MUTED), "请点击识别"

        def info(label, value):
            return ft.Row([t.text(label, 12, t.MUTED, width=110),
                           value if isinstance(value, ft.Control) else t.text(value, 12.5, font_family=t.MONO)])

        is_radio = p.device == self.app.settings.radio_port
        name = t.field(value=self.name_of(p.device), hint="无线设备、嗅探器…", width=220,
                       disabled=not isinstance(ident, board.Identity), on_submit=self._rename)
        body = ft.Column([
            info("串口", p.device),
            info("USB 芯片", p.bridge),
            info("Wi-Fi MAC", mac),
            info("固件", firmware),
            info("名称", ft.Row([name, t.icon_button(ft.Icons.CHECK_ROUNDED, lambda e: self._rename(e, name),
                                                     "保存名称")], spacing=4)),
            ft.Container(height=2),
            ft.Row([
                t.button("识别", self._identify, ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
                         disabled=self.app.busy or not p.supported),
                t.button("设为无线设备" if not is_radio else "当前无线设备", self._use,
                         ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED if not is_radio else ft.Icons.CHECK_CIRCLE_ROUNDED,
                         filled=False, disabled=is_radio),
            ], spacing=8),
        ], spacing=10)
        note = "识别会重启设备，读取固件和 MAC，并让蓝色指示灯闪烁五秒，便于区分设备。"
        return t.card(self.name_of(p.device) or "ESP32 设备", body, note)

    def _rename(self, e, field=None) -> None:
        field = field or e.control
        ident = self.identities.get(self.selected)
        if isinstance(ident, board.Identity):
            names = self.app.settings.board_names
            if field.value.strip():
                names[ident.sta_mac] = field.value.strip()
            else:
                names.pop(ident.sta_mac, None)
            self.app.settings.save()
            self.render()
            self.control.update()

    def _use(self, e) -> None:
        self.app.settings.radio_port = self.selected
        self.app.settings.save()
        self.log.add(f"[app] {self.selected} 已设为所有会话的无线设备。")
        self.render()
        self.control.update()

    def _identify(self, e) -> None:
        device = self.selected
        if self.app.busy:
            return
        self.app.board_busy = True
        self.log.add(f"[app] 正在打开 {device}；设备将重启。")
        self.render()
        self.control.update()

        def work():
            try:
                ident = board.identify(device)
                self.identities[device] = ident
                self.log.add(f"[app] {ident.firmware}，协议 {ident.protocol}，芯片版本 "
                             f"{ident.chip_revision}，MAC {ident.sta_mac}")
                if ident.current:
                    self.log.add("[app] 设备的蓝色指示灯将闪烁五秒。")
                else:
                    self.log.add("[app] 固件版本低于程序要求，请刷写设备。")
            except serial.SerialException as error:
                self.identities[device] = "串口正忙或没有访问权限"
                self.log.add(f"[app] 无法打开 {device}：{error}")
            except Exception as error:
                self.identities[device] = "未检测到 pokeldn 固件"
                self.log.add(f"[app] pokeldn 固件无响应（{error}）。请在下方刷写设备。")
            finally:
                self.app.board_busy = False
                self.app.ui(lambda: (self.render(), self.control.update()))

        threading.Thread(target=work, daemon=True).start()

    # Flashing

    def firmware(self) -> str:
        chosen = self.app.settings.firmware
        if chosen and os.path.exists(chosen):
            return chosen
        return board.bundled_firmware(self.port())

    def flash_card(self) -> ft.Control:
        image = self.firmware()
        p = self.port()
        bundled = image in (board.FIRMWARE, board.FIRMWARE_S3)
        label = "程序自带的设备专用 pokeldn 固件" if bundled else image
        source = ft.Row([
            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=16, color=t.MUTED),
            t.text(label if image else "当前程序未包含此设备的固件镜像。",
                   12, t.MUTED if image else t.RED, expand=True),
            ft.TextButton("使用其他文件", on_click=self._choose_file, style=ft.ButtonStyle(color=t.MUTED)),
        ], spacing=6)
        flashing = bool(self.app.process and self.app.process.running and self.app.process_label == "flash")
        return t.card("刷写固件", ft.Column([
            t.numbered(FLASH_STEPS),
            source,
            ft.Column([self.progress, self.progress_text], spacing=6),
            t.button("正在刷写…" if flashing else "刷写", self._flash, ft.Icons.BOLT_ROUNDED,
                     disabled=self.app.busy or not image or not p or not p.supported),
        ], spacing=14), "将 pokeldn 无线固件写入所选设备，约需三十秒。")

    async def _choose_file(self, e) -> None:
        files = await self.app.picker.pick_files(allowed_extensions=["bin"],
                                                 file_type=ft.FilePickerFileType.CUSTOM)
        if files and files[0].path:
            self._set_firmware(files[0].path)

    def _set_firmware(self, path: str) -> None:
        self.app.settings.firmware = path
        self.app.settings.save()
        self.render()
        self.control.update()

    def _flash(self, e) -> None:
        if self.app.busy:
            return
        args = board.flash_args(self.selected, self.firmware())
        self.log.clear()
        self.log.add(f"[app] 正在刷写 {self.selected}。")
        self.progress.visible, self.progress.value = True, None
        self.progress_text.value = "正在连接…"
        env = dict(os.environ, NO_COLOR="1", PYTHONUNBUFFERED="1")
        env.pop("POKELDN_RADIO", None)
        self.app.process_label = "flash"
        self.app.process = runner.Process(["--module", "esptool", *args], str(SESSION), env, self._flash_line,
                                          self._flashed)
        self.render()
        self.control.update()

    def _flash_line(self, line: str) -> None:
        self.log.add(line)
        found = PERCENT.findall(line)
        if found and "Writing" in line:
            value = min(float(found[-1]), 100.0) / 100

            def show():
                self.progress.value = value
                self.progress_text.value = f"正在写入 {value:.0%}"
                self.progress.update()
                self.progress_text.update()
            self.app.ui(show)

    def _flashed(self, code: int) -> None:
        def done():
            self.progress.value = 1 if code == 0 else 0
            self.progress_text.value = ("完成。设备已使用新固件重启。" if code == 0 else
                                        "刷写失败。请查看活动日志；按住 BOOT 键通常有帮助。")
            self.progress_text.color = t.GREEN if code == 0 else t.RED
            self.identities.pop(self.selected, None)
            self.render()
            self.control.update()
        self.app.ui(done)

    def help_card(self) -> ft.Control:
        def link(label, url):
            return ft.TextButton(label, on_click=lambda e: self.app.page.run_task(self.app.open_url, url),
                                 style=ft.ButtonStyle(color=t.BLUE, padding=0))

        return t.card("找不到设备？", ft.Column([
            t.text("尝试更换数据线或 USB 接口；许多线仅支持充电。", 12.5),
            ft.Row([t.text("Windows 和 macOS 需要安装设备 USB 芯片的驱动：", 12.5),
                    link("CP210x", board.DRIVERS["Silicon Labs CP210x"]),
                    link("CH340", board.DRIVERS["WCH CH340"])], spacing=6, wrap=True),
            t.text("Linux：授予串口访问权限，然后注销并重新登录：", 12.5),
            ft.Container(t.text("sudo usermod -aG dialout $USER", 12, font_family=t.MONO, selectable=True),
                         bgcolor=t.BG, border_radius=8, padding=10),
            t.text("pokeldn 支持经典 ESP32（ESP32-D0WD、WROOM-32E），本分支也支持刷入专用固件的 "
                   "ESP32-S3。不支持 C3 和 C6。", 12.5, t.MUTED),
        ], spacing=8))
