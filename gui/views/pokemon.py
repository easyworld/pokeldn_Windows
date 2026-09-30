import threading

import flet as ft

from gui import builder
from gui import theme as t

VERSIONS = {"firered": "FR", "leafgreen": "LG"}


class PokemonPicker:
    """Pick a species and PKHeX builds a legal one for the game; or check a file someone brings."""

    def __init__(self, app, game: str, value: dict | None, on_change, version: str = ""):
        self.app, self.game, self.on_change, self.version = app, game, on_change, version
        self.value = dict(value or {})
        self.species = t.dropdown([], None, on_select=self._pick, enable_filter=True, editable=True,
                                  menu_height=320, hint_text="正在加载宝可梦种类…", disabled=True)
        self.level = t.field(value=str(self.value.get("level") or ""), hint="自动", mono=True, width=90,
                             on_change=lambda e: self._set("level", e.control.value))
        self.shiny = t.switch(bool(self.value.get("shiny")), lambda e: self._set("shiny", e.control.value))
        self.nickname = t.field(value=self.value.get("nickname", ""), hint="昵称（可选）", expand=True,
                                on_change=lambda e: self._set("nickname", e.control.value))
        self.build_button = t.button("生成", self._build, ft.Icons.AUTO_AWESOME_ROUNDED, disabled=True)
        self.result = ft.Container()
        self.control = ft.Column([
            ft.Row([ft.Container(self.species, expand=True),
                    ft.Column([t.text("等级", 11, t.MUTED), self.level], spacing=2),
                    ft.Column([t.text("异色", 11, t.MUTED), self.shiny], spacing=2)],
                   spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([self.nickname, self.build_button], spacing=10),
            self.result,
            ft.TextButton("或使用宝可梦文件", on_click=self._use_file,
                          style=ft.ButtonStyle(color=t.MUTED, padding=0)),
        ], spacing=10)
        self._show_result()
        threading.Thread(target=self._load_species, daemon=True).start()

    def _set(self, key, value) -> None:
        self.value[key] = value

    def _pick(self, e) -> None:
        self.value["species"] = int(e.control.value)

    def _load_species(self) -> None:
        try:
            species = builder.SERVICE.species(self.game)
            error = ""
        except Exception as exc:
            species, error = [], str(exc)

        def show():
            if error:
                self.species.hint_text = "不可用"
                self._message(error, t.RED)
            else:
                self.species.options = [ft.DropdownOption(key=str(s["id"]), text=s["name"]) for s in species]
                self.species.value = str(self.value["species"]) if self.value.get("species") else None
                self.species.hint_text = "搜索宝可梦种类"
                self.species.disabled = self.build_button.disabled = False
            self.control.update()
        self.app.ui(show)

    def _build(self, e) -> None:
        if not self.value.get("species"):
            self._message("请先选择宝可梦种类。", t.RED)
            self.control.update()
            return
        self.build_button.disabled = True
        self._message("PKHeX 正在寻找合法的相遇记录…", t.MUTED)
        self.control.update()
        try:
            level = int(self.value.get("level") or 0)
        except ValueError:
            level = 0

        def work():
            try:
                info = builder.SERVICE.make(self.game, self.value["species"], self.app.settings.trainer(),
                                            level, bool(self.value.get("shiny")),
                                            self.value.get("nickname", ""), VERSIONS.get(self.version, ""))
                self.value.update(file=info["file"], summary=builder.summary(info), legal=info["legal"],
                                  encounter=info["encounter"], moves=info["moves"])
                self.on_change(dict(self.value))
                done = self._show_result
            except Exception as exc:
                message = str(exc)
                done = lambda: self._message(message, t.RED)   # noqa: E731
            self.app.ui(lambda: (done(), setattr(self.build_button, "disabled", False), self.control.update()))

        threading.Thread(target=work, daemon=True).start()

    async def _use_file(self, e) -> None:
        files = await self.app.picker.pick_files(
            allowed_extensions=[builder.EXTENSIONS[self.game], "bin", "ek3"],
            file_type=ft.FilePickerFileType.CUSTOM)
        if not files or not files[0].path:
            return
        path = files[0].path
        try:
            info = builder.SERVICE.check(self.game, path)
        except Exception as exc:
            self._message(f"此游戏无法接收该宝可梦：{exc}", t.RED)
            self.control.update()
            return
        self.value.update(file=path, summary=builder.summary(info), legal=info["legal"],
                          encounter=info["encounter"], moves=info["moves"],
                          report="" if info["legal"] else info["report"])
        self.on_change(dict(self.value))
        self._show_result()
        self.control.update()

    def _message(self, text: str, color: str) -> None:
        self.result.content = t.text(text, 12, color, selectable=True)

    def _show_result(self) -> None:
        if not self.value.get("file"):
            self.result.content = None
            return
        legal = self.value.get("legal", False)
        lines = [ft.Row([
            ft.Icon(ft.Icons.VERIFIED_ROUNDED if legal else ft.Icons.GPP_BAD_OUTLINED, size=16,
                    color=t.GREEN if legal else t.RED),
            t.text(self.value.get("summary", ""), 13, weight=ft.FontWeight.W_600, expand=True),
            t.pill("合法" if legal else "不合法", t.GREEN if legal else t.RED),
        ], spacing=8)]
        detail = " · ".join(x for x in (self.value.get("encounter", ""), ", ".join(self.value.get("moves", []))) if x)
        if detail:
            lines.append(t.text(detail, 12, t.MUTED))
        if self.value.get("report"):
            lines.append(t.text(self.value["report"], 11.5, t.RED, selectable=True))
        self.result.content = ft.Container(ft.Column(lines, spacing=4), bgcolor=t.BG, border_radius=10, padding=10)


NAME_LISTS = {"species": "species", "move": "moves", "item": "items", "ball": "balls"}
EMPTY = "-"


class NamePicker:
    """A searchable list of the species, moves, items or balls a game has, by name; the value is the id."""

    def __init__(self, app, game: str, kind: str, value: str, on_change, optional: bool = True):
        self.app, self.game, self.kind, self.optional = app, game, NAME_LISTS[kind], optional
        self.dropdown = t.dropdown([], None, on_select=lambda e: on_change("" if e.control.value == EMPTY
                                                                           else e.control.value),
                                   enable_filter=True, editable=True, menu_height=320,
                                   hint_text="正在加载…", disabled=True)
        self.value = value
        self.control = self.dropdown
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        try:
            names = builder.SERVICE.names(self.game, self.kind)
        except Exception:
            names = None

        def show():
            if names is None:
                self.dropdown.hint_text = "不可用"
            else:
                options = [ft.DropdownOption(key=str(n["id"]), text=n["name"]) for n in names]
                if self.optional:
                    options.insert(0, ft.DropdownOption(key=EMPTY, text="不设置"))
                self.dropdown.options = options
                self.dropdown.value = str(self.value) if self.value else (EMPTY if self.optional else None)
                self.dropdown.hint_text = "搜索"
                self.dropdown.disabled = False
            self.dropdown.update()
        self.app.ui(show)
