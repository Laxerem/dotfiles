#!/usr/bin/env python3
"""Фон и переходы экрана блокировки.

Полноэкранный layer-shell слой (overlay), который рисует весь переход сам:
  блокировка    — снимок рабочего стола приближается к центру и размывается,
                  проявляются размытые обои и частицы эффекта;
  разблокировка — то же в обратную сторону, затем слой исчезает и под ним
                  оказывается настоящий рабочий стол.
lock.sh запускает его под hyprlock с прозрачным фоном (misc:session_lock_xray),
поэтому поверх видны только часы и поле ввода.

  lockfx.py --effect dust --image /path/to/wall.jpg     # для lock.sh
  lockfx.py --effect dust --image ... --preview         # предпросмотр, закрыть — клик/клавиша

Протокол с lock.sh: когда переход к экрану блокировки закончен, печатает «ready»
(только после этого запускается hyprlock — его запуск не мешает анимации);
SIGUSR2 — погасить частицы (в момент ввода пароля, вместе с часами hyprlock);
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
from gi.repository import Gdk, GLib, Graphene, Gsk, Gtk
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
        self.add_tick_callback(self.on_tick)

    def hide_particles(self):
        view = self.view
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
