#!/usr/bin/env python3
"""Выбор обоев для hyprpaper и hyprlock: сетка превью, клик — установить."""

import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Graphene, Gsk, Gtk, Pango

WALL_DIR = Path.home() / ".config/hypr/wallpapers"
EXTS = {".png", ".jpg", ".jpeg"}
CONVERT_EXTS = {".webp", ".avif", ".heic", ".jxl", ".bmp", ".gif", ".tif", ".tiff", ".qoi"}
THUMB_W, THUMB_H, RADIUS = 176, 99, 10
LOCK_CONF = Path.home() / ".config/hypr/lockscreen.conf"  # подключается в hyprlock.conf, читается lock.sh
LOCKFX = Path.home() / ".config/hypr/lockfx.py"
LOCK_EFFECTS = (("none", "Без эффекта"), ("dust", "Пыль"), ("snow", "Снег"), ("fireflies", "Светлячки"))
TABS = (("desktop", "Рабочий стол"), ("lock", "Экран блокировки"))  # вкладки с сеткой обоев
TEXT_TAB = ("text", "Текст")
# Текст на экране блокировки (рисует lockfx.py): настройки — в lockscreen.conf, фразы — в PHRASES_FILE
PHRASES_FILE = Path.home() / ".config/hypr/lockscreen-phrases.txt"
TEXT_ANIMS = (("typewriter", "Печатная машинка"), ("fade", "Плавное появление"))
DEFAULT_TEXT_FONT = "Cormorant Garamond Medium Italic 21"  # как в lockfx.py
DEFAULT_TEXT_SPEED, MIN_TEXT_SPEED, MAX_TEXT_SPEED = 100, 20, 250  # мс на букву
# Задержки текста, с: ключ lockscreen.conf, подпись, по умолчанию (как в lockfx.py), минимум, максимум
TEXT_DELAYS = (
    ("lock_text_idle", "Появление через", 2.5, 0.5, 60),
    ("lock_text_hold", "Показ фразы", 5.5, 1, 60),
    ("lock_text_gap", "Пауза между фразами", 0.9, 0, 30),
)

# Пользовательский ~/.config/gtk-4.0/gtk.css (тема Space-transparency) грузится с приоритетом USER
# и ломает виджеты, поэтому стили приложения заданы явно и подключаются поверх него.
CSS = b"""
window.wp, window.wp * { font-family: Montserrat, sans-serif; text-shadow: none; -gtk-icon-shadow: none; }
window.wp { background: #14161b; color: #d4d7de; border-radius: 12px; }

window.wp headerbar {
  background: #1b1e24; color: #d4d7de; box-shadow: none; border: none;
  border-bottom: 1px solid #272b33; min-height: 44px; padding: 0 8px;
}
window.wp headerbar windowcontrols { margin: 0; }

window.wp button.tool {
  background: #262a32; background-image: none; color: #d4d7de; border: 1px solid #30353e;
  border-radius: 8px; box-shadow: none; min-height: 28px; padding: 0 12px; font-size: 12px;
}
window.wp button.tool:hover { background: #2f343d; }
window.wp button.tool:active { background: #363b45; }
window.wp button.tool image { color: #d4d7de; -gtk-icon-size: 14px; }

window.wp stackswitcher { background: #23272e; border-radius: 9px; padding: 3px; }
window.wp stackswitcher button {
  background: transparent; background-image: none; color: #9298a4; border: none; box-shadow: none;
  border-radius: 7px; min-height: 24px; padding: 0 14px; font-size: 12px; margin: 0;
}
window.wp stackswitcher button:hover { color: #d4d7de; }
window.wp stackswitcher button:checked { background: #3a404b; color: #ffffff; }

window.wp scrolledwindow, window.wp viewport, window.wp flowbox { background: transparent; }
window.wp scrollbar { background: transparent; border: none; }
window.wp scrollbar slider { background: #3a3f49; border-radius: 4px; min-width: 6px; border: none; }

window.wp flowboxchild {
  background: transparent; padding: 0; border-radius: 12px; outline: none;
  border: 2px solid transparent; box-shadow: none;
}
window.wp flowboxchild:hover { background: #1f232a; border-color: #343a45; }
window.wp flowboxchild:focus-visible { border-color: #5a6273; }
window.wp flowboxchild.current { border-color: #7aa2f7; background: rgba(122, 162, 247, 0.12); }

window.wp .card { padding: 4px; }
window.wp .card label { font-size: 11px; color: #a9afba; }
window.wp flowboxchild.current .card label { color: #c9d8ff; font-weight: 600; }

window.wp .empty { color: #6c7280; font-size: 13px; }

window.wp .fxbar { padding: 10px 12px 0 12px; }
window.wp .fxbar > label { font-size: 12px; color: #9298a4; }
window.wp .fxchoice { background: #23272e; border-radius: 9px; padding: 3px; }
window.wp .fxchoice button {
  background: transparent; background-image: none; color: #9298a4; border: none; box-shadow: none;
  border-radius: 7px; min-height: 24px; padding: 0 12px; font-size: 12px; margin: 0;
}
window.wp .fxchoice button:hover { color: #d4d7de; }
window.wp .fxchoice button:checked { background: #3a404b; color: #ffffff; }

window.wp .textpage { padding: 14px 16px; }
window.wp .textpage .caption { font-size: 12px; color: #9298a4; }
window.wp .textpage .hint { font-size: 11px; color: #6c7280; }
window.wp .textpage .dim { opacity: 0.45; }

window.wp switch {
  background: #2c313a; background-image: none; border: 1px solid #343a45; border-radius: 12px;
  box-shadow: none; min-width: 40px; min-height: 22px;
}
window.wp switch:checked { background: #5a7fd0; border-color: #6b8fe0; }
window.wp switch slider {
  background: #d4d7de; background-image: none; border: none; box-shadow: none;
  border-radius: 10px; min-width: 18px; min-height: 18px; margin: 2px;
}
window.wp switch image { color: transparent; }

window.wp scale { min-width: 220px; padding: 6px 0; }

window.wp spinbutton {
  background: #262a32; background-image: none; color: #d4d7de; border: 1px solid #30353e;
  border-radius: 8px; box-shadow: none; min-height: 28px; font-size: 12px;
}
window.wp spinbutton text { background: transparent; color: #d4d7de; padding: 0 8px; min-width: 40px; }
window.wp spinbutton button {
  background: transparent; background-image: none; color: #9298a4; border: none; box-shadow: none;
  min-height: 26px; min-width: 26px; padding: 0;
}
window.wp spinbutton button:hover { color: #ffffff; background: #2f343d; }
window.wp spinbutton button image { -gtk-icon-size: 12px; }
window.wp scale trough { background: #2c313a; border: none; border-radius: 3px; min-height: 4px; }
window.wp scale highlight { background: #7aa2f7; border-radius: 3px; }
window.wp scale slider {
  background: #d4d7de; background-image: none; border: none; box-shadow: none;
  border-radius: 9px; min-width: 16px; min-height: 16px; margin: -7px;
}
window.wp scale marks label { font-size: 10px; color: #6c7280; }

window.wp fontdialogbutton > button, window.wp button.font {
  background: #262a32; background-image: none; color: #d4d7de; border: 1px solid #30353e;
  border-radius: 8px; box-shadow: none; min-height: 28px; padding: 0 12px; font-size: 12px;
}
window.wp fontdialogbutton > button:hover { background: #2f343d; }
window.wp fontdialogbutton label { color: #d4d7de; }

window.wp .phrases {
  background: #1b1e24; border: 1px solid #2c313a; border-radius: 10px;
}
window.wp .phrases textview, window.wp .phrases textview text {
  background: transparent; color: #d4d7de; font-size: 13px;
}
window.wp .phrases textview { padding: 8px 10px; }
window.wp .phrases textview text selection { background: #3a4a6b; }

window.wp .toast {
  background: rgba(30, 34, 41, 0.95); color: #e6e8ec; border: 1px solid #343a45;
  border-radius: 18px; padding: 8px 16px; font-size: 12px;
}

window.wp popover > contents {
  background: #1f232a; color: #d4d7de; border: 1px solid #343a45; border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4); padding: 4px;
}
window.wp popover button {
  background: transparent; background-image: none; color: #f0a3a3; border: none; box-shadow: none;
  border-radius: 6px; padding: 4px 10px; font-size: 12px;
}
window.wp popover button:hover { background: #2c313a; }
"""


def list_wallpapers():
    return sorted(
        (p for p in WALL_DIR.iterdir() if p.suffix.lower() in EXTS and p.is_file()),
        key=lambda p: p.name.lower(),
    )


def set_wallpaper(path):
    if subprocess.run(["pgrep", "-x", "hyprpaper"], capture_output=True).returncode != 0:
        subprocess.Popen(["hyprpaper"], start_new_session=True)
        time.sleep(0.4)
    hyprctl = ["hyprctl", "hyprpaper"]
    subprocess.run(hyprctl + ["unload", "all"], capture_output=True)
    subprocess.run(hyprctl + ["preload", str(path)], capture_output=True)
    subprocess.run(hyprctl + ["wallpaper", f",{path}"], capture_output=True)


def get_desktop_wallpaper():
    out = subprocess.run(["hyprctl", "hyprpaper", "listactive"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        _, sep, value = line.partition(": ")
        if sep and value.strip():
            return Path(value.strip())
    return None


def read_lock_conf():
    """Переменные lockscreen.conf: {"lock_bg": ..., "lock_fx": ...}."""
    values = {}
    try:
        for line in LOCK_CONF.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip().startswith("$"):
                values[key.strip()[1:]] = value.strip()
    except OSError:
        pass
    return values


def update_lock_conf(**changes):
    values = read_lock_conf() | changes
    LOCK_CONF.write_text("".join(f"${key} = {value}\n" for key, value in values.items()))


def get_lock_wallpaper():
    bg = read_lock_conf().get("lock_bg")
    return Path(bg) if bg else None


def set_lock_wallpaper(path):
    update_lock_conf(lock_bg=path)


def get_lock_effect():
    fx = read_lock_conf().get("lock_fx", "none")
    return fx if fx in dict(LOCK_EFFECTS) else "none"


def set_lock_effect(fx):
    update_lock_conf(lock_fx=fx)


def get_text_settings():
    conf = read_lock_conf()
    try:
        speed = int(conf.get("lock_text_speed", DEFAULT_TEXT_SPEED))
    except ValueError:
        speed = DEFAULT_TEXT_SPEED
    anim = conf.get("lock_text_anim", TEXT_ANIMS[0][0])
    return {
        "enabled": conf.get("lock_text", "on") != "off",
        "font": conf.get("lock_text_font") or DEFAULT_TEXT_FONT,
        "speed": min(max(speed, MIN_TEXT_SPEED), MAX_TEXT_SPEED),
        "anim": anim if anim in dict(TEXT_ANIMS) else TEXT_ANIMS[0][0],
        "delays": {key: conf_seconds(conf, key, default, lo, hi) for key, _, default, lo, hi in TEXT_DELAYS},
    }


def conf_seconds(conf, key, default, lo, hi):
    try:
        return min(max(float(conf.get(key, default)), lo), hi)
    except ValueError:
        return default


def read_phrases():
    try:
        return PHRASES_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""


def unique_dest(name):
    dest = WALL_DIR / name
    n = 1
    while dest.exists():
        dest = WALL_DIR / f"{Path(name).stem}-{n}{Path(name).suffix}"
        n += 1
    return dest


def load_thumb(path):
    """Превью в 2x-разрешении, обрезанное до пропорций карточки (режим cover)."""
    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), THUMB_W * 4, -1, True)
    w, h = pb.get_width(), pb.get_height()
    scale = max(THUMB_W * 2 / w, THUMB_H * 2 / h)
    sw, sh = max(THUMB_W * 2, round(w * scale)), max(THUMB_H * 2, round(h * scale))
    pb = pb.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
    pb = pb.new_subpixbuf((sw - THUMB_W * 2) // 2, (sh - THUMB_H * 2) // 2, THUMB_W * 2, THUMB_H * 2)
    return Gdk.Texture.new_for_pixbuf(pb)


class Thumb(Gtk.Widget):
    """Превью со скруглёнными углами.

    Gtk.Picture отдаёт натуральный размер картинки, из-за чего FlowBox раскладывал всё в одну колонку.
    Здесь ширина тянется по сетке, а высота всегда держит пропорции 16:9.
    """

    def __init__(self):
        super().__init__()
        self.texture = None

    def set_texture(self, texture):
        self.texture = texture
        self.queue_draw()

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            return THUMB_W, THUMB_W, -1, -1
        height = round(for_size * THUMB_H / THUMB_W) if for_size > 0 else THUMB_H
        return height, height, -1, -1

    def do_snapshot(self, snapshot):
        rect = Graphene.Rect().init(0, 0, self.get_width(), self.get_height())
        clip = Gsk.RoundedRect()
        clip.init_from_rect(rect, RADIUS)
        snapshot.push_rounded_clip(clip)
        if self.texture:
            snapshot.append_texture(self.texture, rect)
        else:
            color = Gdk.RGBA()
            color.parse("#22262d")
            snapshot.append_color(color, rect)
        snapshot.pop()


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Обои", default_width=800, default_height=400)
        self.add_css_class("wp")
        WALL_DIR.mkdir(parents=True, exist_ok=True)

        css = Gtk.CssProvider()
        css.load_from_data(CSS, -1)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1
        )

        header = Gtk.HeaderBar(show_title_buttons=False)
        add_btn = self.tool_button("list-add-symbolic", "Добавить", self.on_add)
        self.rand_btn = self.tool_button("media-playlist-shuffle-symbolic", "Случайные", self.on_random)
        header.pack_start(add_btn)
        header.pack_end(self.rand_btn)
        self.set_titlebar(header)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.flows = {}
        for tab, title in TABS:
            flow = Gtk.FlowBox(
                selection_mode=Gtk.SelectionMode.NONE,
                homogeneous=True,
                valign=Gtk.Align.START,
                min_children_per_line=1,
                max_children_per_line=12,
                margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
                row_spacing=6, column_spacing=6,
            )
            flow.connect("child-activated", self.on_activated, tab)
            self.flows[tab] = flow
            scroll = Gtk.ScrolledWindow(child=flow, hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
            if tab == "lock":
                page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                page.append(self.effect_bar())
                page.append(scroll)
                self.stack.add_titled(page, tab, title)
            else:
                self.stack.add_titled(scroll, tab, title)
        self.stack.add_titled(self.text_page(), *TEXT_TAB)
        self.stack.connect("notify::visible-child-name", self.on_tab_changed)
        header.set_title_widget(Gtk.StackSwitcher(stack=self.stack))

        self.empty = Gtk.Label(
            label="Пока пусто — перетащите картинки в окно или нажмите «Добавить»",
            css_classes=["empty"], halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
            wrap=True, justify=Gtk.Justification.CENTER, visible=False,
        )
        self.toast = Gtk.Label(
            halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_bottom=14,
            css_classes=["toast"], visible=False,
        )
        self.toast_id = 0
        overlay = Gtk.Overlay(child=self.stack)
        overlay.add_overlay(self.empty)
        overlay.add_overlay(self.toast)
        self.set_child(overlay)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self.on_drop)
        self.add_controller(drop)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", lambda _c, key, *_: key == Gdk.KEY_Escape and (self.close() or True))
        self.add_controller(keys)
        self.connect("close-request", lambda *_: self.flush_pending() or False)

        self.paths = []
        self.current_desktop = None
        self.reload()
        threading.Thread(target=self.fetch_desktop_wallpaper, daemon=True).start()

    @staticmethod
    def tool_button(icon, label, callback):
        box = Gtk.Box(spacing=6)
        box.append(Gtk.Image(icon_name=icon))
        box.append(Gtk.Label(label=label))
        btn = Gtk.Button(child=box, css_classes=["tool"], valign=Gtk.Align.CENTER)
        btn.connect("clicked", callback)
        return btn

    def effect_bar(self):
        """Выбор анимированного эффекта экрана блокировки + предпросмотр."""
        bar = Gtk.Box(spacing=10, css_classes=["fxbar"])
        bar.append(Gtk.Label(label="Эффект"))
        choice = Gtk.Box(css_classes=["fxchoice"])
        current, group = get_lock_effect(), None
        for fx, title in LOCK_EFFECTS:
            btn = Gtk.ToggleButton(label=title, active=fx == current, group=group)
            group = group or btn
            btn.connect("toggled", self.on_effect_toggled, fx)
            choice.append(btn)
        bar.append(choice)
        preview = self.tool_button("media-playback-start-symbolic", "Предпросмотр", self.on_preview)
        preview.set_hexpand(True)
        preview.set_halign(Gtk.Align.END)
        bar.append(preview)
        return bar

    def text_page(self):
        """Текст экрана блокировки: вкл/выкл, анимация, шрифт, скорость, задержки и сами фразы."""
        conf = get_text_settings()
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, css_classes=["textpage"])
        grid = Gtk.Grid(row_spacing=10, column_spacing=14)

        def row(n, title, widget, col=0):
            grid.attach(Gtk.Label(label=title, xalign=0, css_classes=["caption"]), col, n, 1, 1)
            grid.attach(widget, col + 1, n, 1, 1)

        enabled = Gtk.Switch(active=conf["enabled"], halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        enabled.connect("notify::active", self.on_text_enabled)
        row(0, "Показывать текст", enabled)

        anims = Gtk.Box(css_classes=["fxchoice"], halign=Gtk.Align.START)
        group = None
        for anim, title in TEXT_ANIMS:
            btn = Gtk.ToggleButton(label=title, active=anim == conf["anim"], group=group)
            group = group or btn
            btn.connect("toggled", self.on_text_anim_toggled, anim)
            anims.append(btn)
        row(1, "Анимация", anims)

        font = Gtk.FontDialogButton(
            dialog=Gtk.FontDialog(title="Шрифт текста"),
            font_desc=Pango.FontDescription.from_string(conf["font"]),
            use_font=True, use_size=False, halign=Gtk.Align.START,
        )
        font.connect("notify::font-desc", self.on_text_font)
        row(2, "Шрифт", font)

        # Слева — медленно, справа — быстро. В конфиге — мс на букву (меньше — быстрее),
        # поэтому значение шкалы зеркальное: text_speed_ms() переводит обратно
        speed = Gtk.Scale(
            adjustment=Gtk.Adjustment(value=self.text_speed_ms(conf["speed"]), lower=MIN_TEXT_SPEED,
                                      upper=MAX_TEXT_SPEED, step_increment=5, page_increment=20),
            draw_value=False, hexpand=True, margin_start=24, margin_end=24,
        )
        speed.add_mark(MIN_TEXT_SPEED, Gtk.PositionType.BOTTOM, "медленно")
        speed.add_mark(self.text_speed_ms(DEFAULT_TEXT_SPEED), Gtk.PositionType.BOTTOM, "обычно")
        speed.add_mark(MAX_TEXT_SPEED, Gtk.PositionType.BOTTOM, "быстро")
        speed.connect("value-changed", lambda sc: self.save_later(
            "lock_text_speed", lambda: self.text_speed_ms(sc.get_value())))
        grid.attach(Gtk.Label(label="Скорость", xalign=0, css_classes=["caption"]), 0, 3, 1, 1)
        grid.attach(speed, 1, 3, 3, 1)  # на всю ширину, под обеими колонками

        # Задержки — правая колонка
        delays = []
        for n, (key, title, _default, lo, hi) in enumerate(TEXT_DELAYS):
            spin = Gtk.SpinButton(
                adjustment=Gtk.Adjustment(value=conf["delays"][key], lower=lo, upper=hi,
                                          step_increment=0.5, page_increment=5),
                digits=1, numeric=True, valign=Gtk.Align.CENTER,
            )
            spin.connect("value-changed", lambda sp, key=key: self.save_later(
                key, lambda: f"{sp.get_value():g}"))
            box = Gtk.Box(spacing=6, halign=Gtk.Align.START)
            box.append(spin)
            box.append(Gtk.Label(label="с", css_classes=["caption"]))
            row(n, title, box, col=2)
            delays.append(box)
        self.pending_saves = {}

        page.append(grid)

        head = Gtk.Box(spacing=10)
        head.append(Gtk.Label(label="Фразы", xalign=0, css_classes=["caption"]))
        head.append(Gtk.Label(label="по одной на строку, # — комментарий", xalign=0, hexpand=True,
                              css_classes=["hint"]))
        head.append(self.tool_button("media-playback-start-symbolic", "Предпросмотр", self.on_preview))
        page.append(head)

        self.phrases = Gtk.TextBuffer(text=read_phrases())
        self.phrases.connect("changed", self.on_phrases_changed)
        self.phrases_save_id = 0
        view = Gtk.TextView(buffer=self.phrases, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        page.append(Gtk.ScrolledWindow(child=view, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                       css_classes=["phrases"]))

        # Без текста остальные настройки ни на что не влияют — приглушаем их
        self.text_controls = [anims, font, speed, *delays]
        self.update_text_controls(conf["enabled"])
        return page

    @staticmethod
    def text_speed_ms(value):
        """Значение шкалы скорости ↔ мс на букву (преобразование симметричное)."""
        return MIN_TEXT_SPEED + MAX_TEXT_SPEED - round(value)

    def update_text_controls(self, enabled):
        for widget in self.text_controls:
            widget.set_sensitive(enabled)

    def on_text_enabled(self, switch, _pspec):
        enabled = switch.get_active()
        update_lock_conf(lock_text="on" if enabled else "off")
        self.update_text_controls(enabled)
        self.show_toast("Текст включён" if enabled else "Текст выключен")

    def on_text_anim_toggled(self, btn, anim):
        if btn.get_active():
            update_lock_conf(lock_text_anim=anim)
            self.show_toast(f"Анимация: {dict(TEXT_ANIMS)[anim]}")

    def on_text_font(self, btn, _pspec):
        if desc := btn.get_font_desc():
            update_lock_conf(lock_text_font=desc.to_string())
            self.show_toast(f"Шрифт: {desc.to_string()}")

    def save_later(self, key, value):
        """Записать key = value() в lockscreen.conf, когда ползунок/счётчик остановится, а не на каждый шаг."""
        if key in self.pending_saves:
            GLib.source_remove(self.pending_saves[key][0])
        source = GLib.timeout_add(300, self.save_now, key)
        self.pending_saves[key] = (source, value)

    def save_now(self, key):
        _, value = self.pending_saves.pop(key)
        update_lock_conf(**{key: value()})
        return GLib.SOURCE_REMOVE

    def on_phrases_changed(self, _buffer):
        if self.phrases_save_id:
            GLib.source_remove(self.phrases_save_id)
        self.phrases_save_id = GLib.timeout_add(500, self.save_phrases)

    def save_phrases(self):
        self.phrases_save_id = 0
        text = self.phrases.get_text(self.phrases.get_start_iter(), self.phrases.get_end_iter(), False)
        PHRASES_FILE.write_text(text if text.endswith("\n") or not text else text + "\n", encoding="utf-8")
        return GLib.SOURCE_REMOVE

    def flush_pending(self):
        """Несохранённые изменения (ползунки, задержки, фразы) — записать сейчас."""
        for key in list(self.pending_saves):
            GLib.source_remove(self.pending_saves[key][0])
            self.save_now(key)
        if self.phrases_save_id:
            GLib.source_remove(self.phrases_save_id)
            self.save_phrases()

    def on_tab_changed(self, *_):
        grid_tab = self.stack.get_visible_child_name() != TEXT_TAB[0]
        self.rand_btn.set_visible(grid_tab)
        self.empty.set_visible(grid_tab and not self.paths)
        self.mark_current()

    def on_effect_toggled(self, btn, fx):
        if btn.get_active():
            set_lock_effect(fx)
            self.show_toast(f"Эффект: {dict(LOCK_EFFECTS)[fx]}")

    def on_preview(self, _btn):
        self.flush_pending()
        cmd = [sys.executable, str(LOCKFX), "--effect", get_lock_effect(), "--preview"]
        if bg := get_lock_wallpaper():
            cmd += ["--image", str(bg)]
        subprocess.Popen(cmd, start_new_session=True)

    def reload(self):
        self.paths = list_wallpapers()
        for flow in self.flows.values():
            while child := flow.get_first_child():
                flow.remove(child)
            for path in self.paths:
                flow.append(self.make_item(path))
        self.on_tab_changed()
        threading.Thread(target=self.load_thumbs, daemon=True).start()

    def children(self, tab):
        child = self.flows[tab].get_first_child()
        while child:
            yield child
            child = child.get_next_sibling()

    def make_item(self, path):
        thumb = Thumb()
        label = Gtk.Label(label=path.stem, ellipsize=3, max_width_chars=1, hexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, css_classes=["card"])
        box.append(thumb)
        box.append(label)
        box.path, box.thumb = path, thumb
        box.set_tooltip_text(path.name)

        right = Gtk.GestureClick(button=3)
        right.connect("pressed", self.on_right_click, box)
        box.add_controller(right)
        return box

    def load_thumbs(self):
        # Одна загрузка превью на файл — раздаём её карточкам во всех вкладках
        for children in zip(*(list(self.children(tab)) for tab, _ in TABS)):
            try:
                texture = load_thumb(children[0].get_child().path)
            except GLib.Error:
                continue
            for child in children:
                GLib.idle_add(child.get_child().thumb.set_texture, texture)

    def fetch_desktop_wallpaper(self):
        path = get_desktop_wallpaper()
        GLib.idle_add(self.set_current_desktop, path)

    def set_current_desktop(self, path):
        self.current_desktop = path
        self.mark_current()

    def mark_current(self):
        current = {"desktop": self.current_desktop, "lock": get_lock_wallpaper()}
        for tab, _ in TABS:
            for child in self.children(tab):
                if child.get_child().path == current[tab]:
                    child.add_css_class("current")
                else:
                    child.remove_css_class("current")

    def apply(self, path, tab):
        if tab == "lock":
            set_lock_wallpaper(path)
            self.mark_current()
            self.show_toast(f"Экран блокировки: {path.stem}")
        else:
            threading.Thread(target=set_wallpaper, args=(path,), daemon=True).start()
            self.set_current_desktop(path)
            self.show_toast(f"Рабочий стол: {path.stem}")

    def on_activated(self, _flow, child, tab):
        self.apply(child.get_child().path, tab)

    def on_random(self, _btn):
        if self.paths:
            self.apply(random.choice(self.paths), self.stack.get_visible_child_name())

    def on_right_click(self, _gesture, _n, x, y, item):
        pop = Gtk.Popover(has_arrow=False)
        btn = Gtk.Button(label="Удалить (в корзину)")
        btn.connect("clicked", lambda *_: (pop.popdown(), self.trash(item.path)))
        pop.set_child(btn)
        pop.set_parent(item)
        pop.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y), width=1, height=1))
        pop.connect("closed", lambda p: GLib.idle_add(p.unparent))
        pop.popup()

    def trash(self, path):
        try:
            Gio.File.new_for_path(str(path)).trash(None)
        except GLib.Error as e:
            self.show_toast(f"Не удалось удалить: {e.message}")
            return
        self.reload()

    def on_add(self, _btn):
        dialog = Gtk.FileDialog(title="Добавить обои")
        flt = Gtk.FileFilter(name="Изображения")
        for ext in EXTS | CONVERT_EXTS:
            flt.add_suffix(ext[1:])
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(flt)
        dialog.set_filters(filters)
        dialog.open_multiple(self, None, self.on_files_chosen)

    def on_files_chosen(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error:
            return
        self.add_files([Path(f.get_path()) for f in files])

    def on_drop(self, _target, file_list, _x, _y):
        self.add_files([Path(f.get_path()) for f in file_list.get_files() if f.get_path()])
        return True

    def add_files(self, files):
        added = converted = 0
        for src in files:
            ext = src.suffix.lower()
            if not src.is_file():
                continue
            if ext in EXTS:
                shutil.copy2(src, unique_dest(src.name))
            elif ext in CONVERT_EXTS:
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file(str(src))
                    pb.savev(str(unique_dest(src.stem + ".png")), "png", [], [])
                except GLib.Error as e:
                    self.show_toast(f"Не удалось конвертировать {src.name}: {e.message}")
                    continue
                converted += 1
            else:
                continue
            added += 1
        if added:
            self.reload()
            msg = f"Добавлено файлов: {added}"
            self.show_toast(msg + f" (конвертировано в PNG: {converted})" if converted else msg)

    def show_toast(self, text):
        self.toast.set_label(text)
        self.toast.set_visible(True)
        if self.toast_id:
            GLib.source_remove(self.toast_id)
        self.toast_id = GLib.timeout_add(2000, self.hide_toast)

    def hide_toast(self):
        self.toast.set_visible(False)
        self.toast_id = 0
        return False


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.laxerem.WallpaperPicker")

    def do_activate(self):
        (self.props.active_window or Window(self)).present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
