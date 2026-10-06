#!/usr/bin/env python3
"""Фон и переходы экрана блокировки.

Полноэкранный layer-shell слой (overlay), который рисует весь переход сам:
  блокировка    — снимок рабочего стола приближается к центру и размывается,
                  проявляются размытые обои и частицы эффекта;
  разблокировка — то же в обратную сторону, затем слой исчезает и под ним
                  оказывается настоящий рабочий стол.
lock.sh запускает его под hyprlock с прозрачным фоном (misc:session_lock_xray),
поэтому поверх видны только часы и поле ввода.

Пока компьютер простаивает, на месте поля ввода появляются фразы из
lockscreen-phrases.txt (как подсказки на загрузочном экране в играх) — печатаются
по буквам или плавно проявляются целиком ($lock_text_anim); при вводе
текст растворяется, а hyprlock показывает поле ввода. Простой определяется
по протоколу ext-idle-notify.

  lockfx.py --effect dust --image /path/to/wall.jpg     # для lock.sh
  lockfx.py --effect dust --image ... --preview         # предпросмотр, закрыть — клик/клавиша

Протокол с lock.sh: когда переход к экрану блокировки закончен, печатает «ready»
(только после этого запускается hyprlock — его запуск не мешает анимации);
SIGUSR2 — погасить частицы и текст (в момент ввода пароля, вместе с часами hyprlock);
SIGUSR1 — обратный переход и выход.
"""

import argparse
import math
import os
import random
import signal
import subprocess
import sys

LAYER_SHELL_LIB = "/usr/lib/libgtk4-layer-shell.so"
# gtk4-layer-shell должен загрузиться раньше libwayland-client
if LAYER_SHELL_LIB not in os.environ.get("LD_PRELOAD", ""):
    os.environ["LD_PRELOAD"] = ":".join(filter(None, [LAYER_SHELL_LIB, os.environ.get("LD_PRELOAD")]))
    os.execv(sys.executable, [sys.executable, *sys.argv])

# Снимок рабочего стола делаем сразу, пока грузится GTK (~30 мс; без сжатия — быстрее)
SCREENSHOT = subprocess.Popen(["grim", "-l", "0", "-t", "png", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Graphene, Gsk, Gtk, Pango
from gi.repository import Gtk4LayerShell as LayerShell

try:
    gi.require_version("GLibUnix", "2.0")
    from gi.repository import GLibUnix
    signal_add = GLibUnix.signal_add
except (ImportError, ValueError):
    signal_add = GLib.unix_signal_add

EFFECTS = {"none": "Без эффекта", "dust": "Пыль", "snow": "Снег", "fireflies": "Светлячки"}
BLUR_RADIUS = 18      # примерно как blur в hyprlock.conf
DIM = 0.12            # затемнение обоев (brightness ≈ 0.9 в hyprlock.conf)
ZOOM = 1.08           # насколько «наезжает» рабочий стол
TIME_IN = 1.1         # длительность перехода при блокировке, с
TIME_OUT = 0.9        # и при разблокировке
FINAL_FADE = 0.35     # в конце разблокировки слой растворяется в настоящий рабочий стол
FX_IN = 1.6           # частицы проявляются после перехода, с
FX_OUT = 0.35         # и гаснут первыми при разблокировке
MAX_DT = 1 / 40       # шаг анимации не больше этого: после подвисания — продолжаем, а не прыгаем

# Текст на экране блокировки. Шрифт, скорость, анимация и вкл/выкл задаются в «Обоях» и хранятся
# в lockscreen.conf ($lock_text, $lock_text_font, $lock_text_speed, $lock_text_anim), фразы — в PHRASES_FILE.
LOCK_CONF = os.path.expanduser("~/.config/hypr/lockscreen.conf")
PHRASES_FILE = os.path.expanduser("~/.config/hypr/lockscreen-phrases.txt")
DEFAULT_PHRASES = ["Даже самая долгая ночь заканчивается рассветом.", "Отдых — это тоже часть пути."]
DEFAULT_FONT = "Cormorant Garamond Medium Italic 21"
DEFAULT_SPEED_MS = 100  # средняя пауза между буквами
TEXT_ANIMS = ("typewriter", "fade")  # печатная машинка / плавное появление
FADE_CHARS = 12       # плавное появление длится столько «букв» (100 мс → 1.2 с)
FADE_RISE = 10        # и всплывает снизу на столько пикселей
TEXT_Y = 100          # на месте поля ввода: position = 0, -100 в hyprlock-widgets.conf
# Задержки по умолчанию; настраиваются в «Обоях» ($lock_text_idle, $lock_text_hold, $lock_text_gap)
IDLE_SHOW = 2.5       # текст появляется после стольких секунд без ввода
IDLE_AFTER_INPUT = 10 # а если уже начинали вводить — позже, чтобы не лечь поверх точек пароля
HOLD_TIME = 5.5       # фраза напечатана — держим (курсор мигает)
ERASE_SPEED = 0.35    # стирание «бэкспейсом» быстрее печати во столько раз
GAP_TIME = 0.9        # пустая строка с мигающим курсором перед следующей фразой
DASH_PAUSE = 8        # перед подписью автора машинка «задумывается» на столько букв
AUTHOR_SCALE = 0.82   # подпись автора мельче цитаты
AUTHOR_ALPHA = 0.7    # и приглушённее
AUTHOR_GAP = 7        # отступ между цитатой и подписью, px
BLINK_PERIOD = 1.05   # период мигания курсора, с
HIDE_TIME = 0.25      # быстрое исчезновение при вводе


def ease_out_cubic(k):
    return 1 - (1 - k) ** 3


def stage(p, start, end):
    """Часть перехода p ∈ [start, end] → 0..1 с мягкими краями (smoothstep)."""
    k = min(max((p - start) / (end - start), 0.0), 1.0)
    return k * k * (3 - 2 * k)


def ease_in_out_sine(k):
    return -(math.cos(math.pi * k) - 1) / 2


def ease_in_out_cubic(k):
    return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2


def glow_texture(rgb, core=0.25, size=64):
    """Мягкая круглая точка: яркое ядро + ореол, затухающий к краю."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    c = size / 2
    grad = cairo.RadialGradient(c, c, 0, c, c, c)
    r, g, b = (v / 255 for v in rgb)
    grad.add_color_stop_rgba(0, r, g, b, 1)
    grad.add_color_stop_rgba(core, r, g, b, 0.85)
    grad.add_color_stop_rgba(core + (1 - core) * 0.35, r, g, b, 0.18)
    grad.add_color_stop_rgba(1, r, g, b, 0)
    ctx.set_source(grad)
    ctx.paint()
    surface.flush()
    return Gdk.MemoryTexture.new(
        size, size, Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
        GLib.Bytes.new(bytes(surface.get_data())), surface.get_stride(),
    )


class Particle:
    __slots__ = ("x", "y", "z", "vx", "vy", "size", "alpha", "phase", "freq", "heading")


class Effect:
    """Базовый эффект: набор частиц, которые зацикливаются по краям экрана."""

    density = 26000   # пикселей экрана на одну частицу
    color = (255, 255, 255)
    core = 0.25
    margin = 30

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.texture = glow_texture(self.color, self.core)
        self.particles = [self.spawn(random.uniform(0, w), random.uniform(0, h))
                          for _ in range(max(8, int(w * h / self.density)))]

    def spawn(self, x, y):
        p = Particle()
        p.x, p.y = x, y
        p.z = random.random() ** 1.5           # глубина: дальних частиц больше
        p.phase = random.uniform(0, math.tau)
        p.freq = random.uniform(0.3, 1.2)
        p.heading = random.uniform(0, math.tau)
        self.init(p)
        return p

    def init(self, p):
        raise NotImplementedError

    def step(self, p, dt, t):
        raise NotImplementedError

    def opacity(self, p, t):
        return p.alpha

    def update(self, dt, t):
        m, w, h = self.margin, self.w, self.h
        for p in self.particles:
            self.step(p, dt, t)
            if p.x < -m:
                p.x += w + 2 * m
            elif p.x > w + m:
                p.x -= w + 2 * m
            if p.y < -m:
                p.y += h + 2 * m
            elif p.y > h + m:
                p.y -= h + 2 * m

    def draw(self, snapshot, t):
        rect = Graphene.Rect()
        for p in self.particles:
            a = self.opacity(p, t)
            if a <= 0.01:
                continue
            r = p.size
            snapshot.push_opacity(min(a, 1.0))
            snapshot.append_texture(self.texture, rect.init(p.x - r, p.y - r, 2 * r, 2 * r))
            snapshot.pop()


class Dust(Effect):
    """Пылинки в луче света: медленно парят вверх, покачиваются и мерцают."""

    color = (255, 240, 215)
    core = 0.18

    def init(self, p):
        p.size = 3 + 9 * p.z
        p.vx = random.uniform(-5, 5) * (0.4 + p.z)
        p.vy = -random.uniform(2, 9) * (0.4 + p.z)
        p.alpha = 0.12 + 0.45 * p.z

    def step(self, p, dt, t):
        p.x += (p.vx + 6 * math.sin(t * p.freq * 0.5 + p.phase)) * dt
        p.y += (p.vy + 3 * math.cos(t * p.freq * 0.4 + p.phase)) * dt

    def opacity(self, p, t):
        return p.alpha * (0.55 + 0.45 * math.sin(t * p.freq * 1.6 + p.phase))


class Snow(Effect):
    """Снег: падает с лёгким ветром, ближние хлопья крупнее и быстрее."""

    density = 14000
    core = 0.35

    def init(self, p):
        p.size = 2.5 + 7 * p.z
        p.vy = 25 + 70 * p.z
        p.vx = random.uniform(-8, 8)
        p.alpha = 0.25 + 0.55 * p.z

    def step(self, p, dt, t):
        wind = 14 * math.sin(t * 0.15) * (0.5 + p.z)
        p.x += (p.vx + wind + 12 * math.sin(t * p.freq + p.phase)) * dt
        p.y += p.vy * dt


class Fireflies(Effect):
    """Светлячки: блуждают по плавным траекториям и мягко пульсируют."""

    density = 90000
    color = (215, 255, 130)
    core = 0.12
    margin = 60

    def init(self, p):
        p.size = 14 + 18 * p.z
        p.vx = 12 + 22 * p.z          # скорость
        p.alpha = 0.5 + 0.5 * p.z

    def step(self, p, dt, t):
        p.heading += math.sin(t * p.freq + p.phase) * 1.2 * dt
        p.x += math.cos(p.heading) * p.vx * dt
        p.y += math.sin(p.heading) * p.vx * dt

    def opacity(self, p, t):
        pulse = 0.5 + 0.5 * math.sin(t * p.freq * 1.3 + p.phase)
        return p.alpha * (0.15 + 0.85 * pulse ** 3)


EFFECT_CLASSES = {"none": None, "dust": Dust, "snow": Snow, "fireflies": Fireflies}


def read_lock_conf():
    values = {}
    try:
        with open(LOCK_CONF, encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.partition("=")
                if sep and key.strip().startswith("$"):
                    values[key.strip()[1:]] = value.strip()
    except OSError:
        pass
    return values


def conf_seconds(conf, key, default):
    try:
        return max(0.0, float(conf.get(key, default)))
    except ValueError:
        return default


def split_quote(phrase):
    """«Цитата - Автор» → (цитата, автор). Автор — после последнего тире между пробелами,
    если это похоже на имя: с заглавной буквы и недлинное. Иначе фраза остаётся как есть."""
    for i in range(len(phrase) - 1, 0, -1):
        if phrase[i] in "-–—" and phrase[i - 1].isspace() and phrase[i + 1:i + 2].isspace():
            quote, author = phrase[:i].rstrip(), phrase[i + 1:].strip().rstrip(".")
            if quote and author[:1].isupper() and len(author) <= 40 and len(author.split()) <= 5:
                return quote, author
            break
    return phrase.strip(), None


def load_phrases():
    try:
        with open(PHRASES_FILE, encoding="utf-8") as f:
            phrases = [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]
    except OSError:
        phrases = []
    return phrases or DEFAULT_PHRASES


class IdleWatcher:
    """ext-idle-notify: idled — нет ввода timeout секунд, resumed — ввод появился.

    Отдельное Wayland-соединение (pywayland), встроенное в главный цикл GLib.
    Работает и под экраном блокировки — так же, как hypridle.
    """

    def __init__(self, timeout, on_idle, on_resume):
        from pywayland.client import Display
        from pywayland.protocol.ext_idle_notify_v1 import ExtIdleNotifierV1
        from pywayland.protocol.wayland import WlSeat

        self.display = Display()
        self.display.connect()
        found = {}

        def on_global(registry, name, interface, version):
            if interface == "wl_seat" and "seat" not in found:
                found["seat"] = registry.bind(name, WlSeat, min(version, 7))
            elif interface == "ext_idle_notifier_v1":
                found["notifier"] = (registry.bind(name, ExtIdleNotifierV1, min(version, 2)), version)

        registry = self.display.get_registry()
        registry.dispatcher["global"] = on_global
        self.display.roundtrip()
        if "seat" not in found or "notifier" not in found:
            raise RuntimeError("нет ext_idle_notifier_v1")
        notifier, version = found["notifier"]
        ms = int(timeout * 1000)
        # v2: только реальный ввод, без учёта idle-inhibit (видео и т.п.)
        self.notification = (notifier.get_input_idle_notification(ms, found["seat"]) if version >= 2
                             else notifier.get_idle_notification(ms, found["seat"]))
        self.notification.dispatcher["idled"] = lambda *_: on_idle()
        self.notification.dispatcher["resumed"] = lambda *_: on_resume()
        self.display.flush()
        GLib.io_add_watch(self.display.get_fd(), GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN, self.on_readable)

    def on_readable(self, *_):
        self.display.dispatch(block=True)
        self.display.flush()
        return GLib.SOURCE_CONTINUE


class Typewriter:
    """Сменяющиеся фразы, два вида анимации:
      typewriter — буквы появляются одна за другой в живом ритме (задержки на
                   знаках препинания), за текстом мигает курсор; дочитанная фраза
                   стирается «бэкспейсом»;
      fade       — фраза целиком проявляется, всплывая снизу, и так же растворяется.
    После паузы появляется следующая."""

    def __init__(self, phrases, font, char_time, anim="typewriter", hold=HOLD_TIME, gap=GAP_TIME):
        self.phrases = phrases
        self.hold, self.gap = hold, gap
        self.fade = anim == "fade"
        self.font = Pango.FontDescription.from_string(font)
        self.char_time = char_time
        self.queue = []
        self.text = ""
        self.author_at = None     # где в тексте начинается подпись автора (нет автора — None)
        self.times = []           # момент появления каждой буквы
        self.state, self.t = "off", 0.0
        self.visible = Transition()
        self.wanted = False

    def next_phrase(self, state):
        if not self.queue:
            self.queue = random.sample(self.phrases, len(self.phrases))
            if len(self.queue) > 1 and self.queue[-1] == self.text:
                self.queue.insert(0, self.queue.pop())
        quote, author = split_quote(self.queue.pop())
        self.text = quote if author is None else f"{quote}\n{author}"
        self.author_at = None if author is None else len(quote)    # индекс «\n» перед подписью
        self.state, self.t = state, 0.0
        if self.fade:
            self.type_end = self.char_time * FADE_CHARS
            return
        ct, t, self.times = self.char_time, 0.0, []
        for i, ch in enumerate(self.text):
            if i == self.author_at:      # перед подписью автора — пауза, как будто задумались
                t += ct * DASH_PAUSE
            t += ct * random.uniform(0.55, 1.45)
            self.times.append(t)
            if ch in ".!?…":
                t += ct * 6
            elif ch in ",;:—":
                t += ct * 3
            elif ch == " ":
                t += ct * 0.4
        self.type_end = t + ct

    def show(self):
        if self.wanted:
            return
        self.wanted = True
        self.visible.value = 1.0
        self.visible.go(1.0, 0.01, ease_out_cubic)
        self.next_phrase("gap")

    def hide(self):
        if not self.wanted:
            return
        self.wanted = False
        self.visible.go(0.0, HIDE_TIME, ease_out_cubic)

    def erase_count(self):
        if self.fade:
            return len(self.text) if self.t < self.type_end else 0
        return max(0, len(self.text) - int(self.t / (self.char_time * ERASE_SPEED)))

    def fade_value(self):
        """Плавное появление: 0 — фразы не видно, 1 — проявилась полностью."""
        if self.state == "typing":
            return ease_out_cubic(min(self.t / self.type_end, 1.0))
        if self.state == "erasing":
            return 1 - ease_in_out_sine(min(self.t / self.type_end, 1.0))
        return 1.0 if self.state == "hold" else 0.0

    def step(self, dt):
        self.visible.step(dt)
        if self.state == "off":
            return
        if not self.wanted and self.visible.done:
            self.state, self.text = "off", ""
            return
        self.t += dt
        if self.state == "gap" and self.t >= self.gap:
            self.state, self.t = "typing", 0.0
        elif self.state == "typing" and self.t >= self.type_end:
            self.state, self.t = "hold", 0.0
        elif self.state == "hold" and self.t >= self.hold:
            self.state, self.t = "erasing", 0.0
        elif self.state == "erasing" and self.erase_count() == 0:
            self.next_phrase("gap")

    def shown(self):
        """Сколько букв сейчас на экране."""
        if self.fade:
            return len(self.text) if self.state != "gap" else 0
        if self.state == "typing":
            return sum(1 for t in self.times if t <= self.t)
        if self.state == "hold":
            return len(self.text)
        if self.state == "erasing":
            return self.erase_count()
        return 0

    def caret_alpha(self):
        if self.fade:
            return 0.0
        if self.state in ("typing", "erasing"):
            return 1.0                      # во время печати курсор не мигает
        return 0.5 + 0.5 * math.cos(math.tau * self.t / BLINK_PERIOD)

    def draw(self, snapshot, widget, w, h, alpha):
        alpha *= self.visible.value
        rise = 0.0
        if self.fade:
            k = self.fade_value()
            alpha *= k
            rise = FADE_RISE * (1 - k) if self.state == "typing" else 0.0
        if self.state == "off" or alpha < 0.005:
            return
        layout = widget.create_pango_layout(self.text)
        layout.set_font_description(self.font)
        box_w = int(w * 0.7)
        layout.set_width(box_w * Pango.SCALE)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_wrap(Pango.WrapMode.WORD)
        layout.set_spacing(AUTHOR_GAP * Pango.SCALE)
        # Положение — по всей фразе, чтобы строка не сдвигалась по мере печати
        _, logical = layout.get_pixel_extents()
        n = self.shown()
        cut = len(self.text[:n].encode())        # индексы Pango — в байтах UTF-8
        end = len(self.text.encode())
        attrs = Pango.AttrList()

        def add(attr, start, stop):
            attr.start_index, attr.end_index = start, stop
            attrs.insert(attr)

        if self.author_at is not None:
            # Подпись автора — мельче и приглушённее. Pango применяет атрибуты одного типа в порядке
            # начала диапазона, поэтому приглушаем только уже напечатанную часть подписи, а скрытие
            # ещё не напечатанного (cut..end) не пересекаем с ней.
            start = len(self.text[:self.author_at].encode()) + 1     # после «\n»
            add(Pango.attr_scale_new(AUTHOR_SCALE), start, end)
            if cut > start:
                add(Pango.attr_foreground_alpha_new(int(65535 * AUTHOR_ALPHA)), start, cut)
        if cut < end:
            add(Pango.attr_foreground_alpha_new(1), cut, end)
        layout.set_attributes(attrs)
        color = Gdk.RGBA(red=1, green=0.97, blue=0.92, alpha=0.9)

        snapshot.save()
        snapshot.translate(Graphene.Point().init((w - box_w) / 2, h / 2 + TEXT_Y - logical.height / 2 + rise))
        snapshot.push_opacity(alpha)
        shadow = Gsk.Shadow()
        shadow.color = Gdk.RGBA(red=0, green=0, blue=0, alpha=0.6)
        shadow.dx, shadow.dy, shadow.radius = 0, 1, 6
        snapshot.push_shadow([shadow])
        snapshot.append_layout(layout, color)
        # Курсор — тонкая черта сразу за последней напечатанной буквой
        caret = self.caret_alpha()
        if caret > 0.01:
            pos = layout.index_to_pos(cut)
            x, y, ch = pos.x / Pango.SCALE, pos.y / Pango.SCALE, pos.height / Pango.SCALE
            snapshot.append_color(Gdk.RGBA(red=color.red, green=color.green, blue=color.blue, alpha=0.85 * caret),
                                  Graphene.Rect().init(x + 1, y + ch * 0.15, 2, ch * 0.75))
        snapshot.pop()
        snapshot.pop()
        snapshot.restore()


def read_screenshot():
    data, _ = SCREENSHOT.communicate()
    if SCREENSHOT.returncode != 0 or not data:
        return None
    try:
        return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
    except GLib.Error:
        return None


class Transition:
    """Плавное изменение значения от текущего к target.

    Время копится из шагов кадров (не по часам), поэтому если кадры на миг
    остановятся, анимация продолжится с того же места, а не прыгнет вперёд.
    """

    def __init__(self):
        self.value = self.start_value = self.target = 0.0
        self.elapsed, self.duration, self.ease = 0.0, 1.0, ease_out_cubic
        self.done = True

    def go(self, target, duration, ease, delay=0.0):
        self.start_value, self.target = self.value, target
        self.elapsed, self.duration, self.ease = -delay, duration, ease
        self.done = False

    def step(self, dt):
        """Продвигает анимацию на dt секунд; True — закончена."""
        if not self.done:
            self.elapsed += dt
            k = min(max(self.elapsed, 0.0) / self.duration, 1.0)
            self.value = self.start_value + (self.target - self.start_value) * self.ease(k)
            self.done = k >= 1
        return self.done


class FxView(Gtk.Widget):
    def __init__(self, effect_cls, image, screenshot):
        super().__init__(hexpand=True, vexpand=True)
        self.effect_cls = effect_cls
        self.wallpaper = Gdk.Texture.new_from_filename(image) if image else None
        self.shot = screenshot
        self.size = None
        self.background = self.shot_blurred = self.effect = None
        self.progress = Transition()      # 0 — рабочий стол, 1 — экран блокировки
        self.fx_alpha = Transition()      # прозрачность частиц
        conf = read_lock_conf()
        try:
            speed = max(10, int(conf.get("lock_text_speed", DEFAULT_SPEED_MS))) / 1000
        except ValueError:
            speed = DEFAULT_SPEED_MS / 1000
        self.text_enabled = conf.get("lock_text", "on") != "off"
        anim = conf.get("lock_text_anim", TEXT_ANIMS[0])
        self.idle_show = max(0.5, conf_seconds(conf, "lock_text_idle", IDLE_SHOW))
        self.typewriter = Typewriter(load_phrases(), conf.get("lock_text_font") or DEFAULT_FONT, speed,
                                     anim if anim in TEXT_ANIMS else TEXT_ANIMS[0],
                                     hold=conf_seconds(conf, "lock_text_hold", HOLD_TIME),
                                     gap=conf_seconds(conf, "lock_text_gap", GAP_TIME))
        self.now = 0.0

    def render(self, w, h, draw):
        snap = Gtk.Snapshot()
        draw(snap)
        return self.get_native().get_renderer().render_texture(snap.to_node(), Graphene.Rect().init(0, 0, w, h))

    @staticmethod
    def append_blurred(snap, texture, w, h):
        """Текстура cover-ом с размытием; поля на радиус размытия — чтобы края не темнели."""
        tw, th = texture.get_width(), texture.get_height()
        pad = BLUR_RADIUS * 2
        scale = max((w + 2 * pad) / tw, (h + 2 * pad) / th)
        sw, sh = tw * scale, th * scale
        snap.push_blur(BLUR_RADIUS)
        snap.append_scaled_texture(texture, Gsk.ScalingFilter.TRILINEAR,
                                   Graphene.Rect().init((w - sw) / 2, (h - sh) / 2, sw, sh))
        snap.pop()

    def prepare(self, w, h):
        """Тяжёлое (размытие) рендерим один раз в текстуры."""
        full = Graphene.Rect().init(0, 0, w, h)
        black = Gdk.RGBA(red=0, green=0, blue=0, alpha=1)

        def background(snap):
            snap.append_color(black, full)
            if self.wallpaper:
                self.append_blurred(snap, self.wallpaper, w, h)
            snap.append_color(Gdk.RGBA(red=0, green=0, blue=0, alpha=DIM), full)

        self.background = self.render(w, h, background)
        if self.shot:
            self.shot_blurred = self.render(w, h, lambda snap: (
                snap.append_color(black, full), self.append_blurred(snap, self.shot, w, h)))
        self.effect = self.effect_cls(w, h) if self.effect_cls else None
        self.size = (w, h)

    def advance(self, dt):
        self.now += dt
        if self.effect and self.fx_alpha.value > 0:
            self.effect.update(dt, self.now)
        self.typewriter.step(dt)
        self.queue_draw()

    def do_snapshot(self, snapshot):
        w, h = self.get_width(), self.get_height()
        if w <= 0 or h <= 0:
            return
        if self.size != (w, h):
            self.prepare(w, h)
        full = Graphene.Rect().init(0, 0, w, h)
        p = self.progress.value

        # Рабочий стол: приближается к центру и размывается
        if self.shot and p < 1:
            s = 1 + (ZOOM - 1) * p
            snapshot.save()
            snapshot.translate(Graphene.Point().init(w / 2, h / 2))
            snapshot.scale(s, s)
            snapshot.translate(Graphene.Point().init(-w / 2, -h / 2))
            snapshot.append_texture(self.shot, full)
            # резкость уходит в первой половине перехода
            snapshot.push_opacity(stage(p, 0.0, 0.6))
            snapshot.append_texture(self.shot_blurred, full)
            snapshot.pop()
            snapshot.restore()

        # Обои и частицы проявляются поверх
        if p > 0 or not self.shot:
            # обои проявляются во второй половине
            snapshot.push_opacity(stage(p, 0.3, 1.0) if self.shot else 1.0)
            snapshot.append_texture(self.background, full)
            if self.effect and self.fx_alpha.value > 0.005:
                snapshot.push_opacity(self.fx_alpha.value)
                self.effect.draw(snapshot, self.now)
                snapshot.pop()
            snapshot.pop()

        # Текст — только на полностью проявившемся экране блокировки
        self.typewriter.draw(snapshot, self, w, h, stage(p, 0.9, 1.0) if self.shot else 1.0)


class FxWindow(Gtk.Window):
    def __init__(self, app, args):
        super().__init__(application=app, decorated=False)
        LayerShell.init_for_window(self)
        LayerShell.set_namespace(self, "lockfx")
        LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(self, edge, True)
        LayerShell.set_exclusive_zone(self, -1)
        LayerShell.set_keyboard_mode(
            self, LayerShell.KeyboardMode.EXCLUSIVE if args.preview else LayerShell.KeyboardMode.NONE
        )
        self.add_css_class("lockfx")

        self.view = FxView(EFFECT_CLASSES[args.effect], args.image, read_screenshot())
        if args.preview:
            overlay = Gtk.Overlay(child=self.view)
            self.hint = Gtk.Label(
                label=f"Предпросмотр: {EFFECTS[args.effect]} — нажмите любую клавишу или кликните, чтобы закрыть",
                halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_bottom=40, css_classes=["osd"],
            )
            overlay.add_overlay(self.hint)
            self.set_child(overlay)
            keys = Gtk.EventControllerKey()
            keys.connect("key-pressed", lambda *_: self.close_animated() or True)
            self.add_controller(keys)
            click = Gtk.GestureClick()
            click.connect("pressed", lambda *_: self.close_animated())
            self.add_controller(click)
        else:
            self.hint = None
            self.set_child(self.view)

        self.frames = 0
        self.last = None
        self.ready_sent = False
        self.closing = False
        self.preview = args.preview
        self.had_input = False
        self.show_timer = 0
        self.idle = None
        if not args.preview:
            try:
                self.idle = IdleWatcher(self.view.idle_show, self.on_idle, self.on_input)
            except Exception as e:  # без протокола просто не показываем текст
                print(f"lockfx: idle-notify недоступен: {e}", file=sys.stderr)
        self.add_tick_callback(self.on_tick)

    def on_idle(self):
        if self.closing:
            return
        if self.had_input:
            # Уже начинали вводить пароль — ждём дольше, чтобы не лечь поверх точек
            self.cancel_show_timer()
            wait = max(IDLE_AFTER_INPUT - self.view.idle_show, 0.0)
            self.show_timer = GLib.timeout_add(int(wait * 1000), self.show_text)
        else:
            self.show_text()

    def on_input(self):
        self.had_input = True
        self.cancel_show_timer()
        self.view.typewriter.hide()

    def cancel_show_timer(self):
        if self.show_timer:
            GLib.source_remove(self.show_timer)
            self.show_timer = 0

    def show_text(self):
        self.show_timer = 0
        if not self.closing and self.view.text_enabled:
            self.view.typewriter.show()
        return GLib.SOURCE_REMOVE

    def hide_particles(self):
        view = self.view
        self.cancel_show_timer()
        view.typewriter.hide()
        if view.fx_alpha.target != 0.0:
            view.fx_alpha.go(0.0, FX_OUT, ease_out_cubic)

    def close_animated(self):
        if self.closing:
            return
        self.closing = True
        if self.hint:
            self.hint.set_visible(False)
        view = self.view
        # Частицы уже гаснут (SIGUSR2) — фон уходит сразу, иначе — чуть позже частиц
        delay = 0.0 if view.fx_alpha.target == 0.0 else FX_OUT * 0.4
        self.hide_particles()
        view.progress.go(0.0, TIME_OUT, ease_in_out_sine, delay=delay)
        self.final_fade = Transition()
        self.final_fade.value = self.final_fade.target = 1.0

    def on_tick(self, _widget, clock):
        now = clock.get_frame_time() / 1e6
        dt = min(now - self.last, MAX_DT) if self.last is not None else 0.0
        self.last = now
        self.frames += 1
        view = self.view
        # Первые кадры — точная копия рабочего стола: незаметно появляемся, потом начинаем переход
        if self.frames == 3 and not self.closing:
            view.progress.go(1.0, TIME_IN, ease_in_out_sine)
            view.fx_alpha.go(1.0, FX_IN, ease_in_out_cubic, delay=TIME_IN * 0.6)
        view.progress.step(dt)
        view.fx_alpha.step(dt)
        view.advance(dt)
        if not self.ready_sent and self.frames > 3 and view.progress.done:
            self.ready_sent = True
            print("ready", flush=True)
            if self.preview:
                GLib.timeout_add(int(self.view.idle_show * 1000), self.show_text)
        if self.closing and view.progress.done and view.fx_alpha.done:
            # Снимок рабочего стола мог устареть — не обрываем, а растворяем слой
            if self.final_fade.done and self.final_fade.target == 0.0:
                self.get_application().quit()
                return GLib.SOURCE_REMOVE
            if self.final_fade.done:
                self.final_fade.go(0.0, FINAL_FADE, ease_in_out_sine)
            self.final_fade.step(dt)
            self.set_opacity(self.final_fade.value)
        return GLib.SOURCE_CONTINUE


class App(Gtk.Application):
    def __init__(self, args):
        super().__init__(application_id=None)
        self.args = args

    def do_activate(self):
        css = Gtk.CssProvider()
        css.load_from_string("window.lockfx { background: transparent; }")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = FxWindow(self, self.args)
        # SOURCE_CONTINUE: повторный SIGUSR1 не должен убить процесс посреди анимации
        signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, lambda: win.close_animated() or GLib.SOURCE_CONTINUE)
        signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, lambda: win.hide_particles() or GLib.SOURCE_CONTINUE)
        signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: self.quit() or GLib.SOURCE_REMOVE)
        win.present()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--effect", choices=EFFECT_CLASSES, default="none")
    parser.add_argument("--image", help="обои экрана блокировки")
    parser.add_argument("--preview", action="store_true", help="закрывается кликом или клавишей")
    args = parser.parse_args()
    return App(args).run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
