# YT-DLP Downloader - Kivy Android App
import os
import threading
import re

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp

# no animation import - causes crash on android/pydroid3
# no filechooser - causes crash on pydroid3

Window.clearcolor = (0.06, 0.05, 0.16, 1)

APP_DIR = "/storage/emulated/0/YT-Downloader"
DL_DIR  = "/storage/emulated/0/Download"

for _d in (APP_DIR, DL_DIR):
    try:
        os.makedirs(_d, exist_ok=True)
    except Exception:
        pass

SUPPORTED = [
    'youtube.com', 'youtu.be', 'instagram.com', 'facebook.com',
    'fb.watch', 'twitter.com', 'x.com', 'tiktok.com',
    'dailymotion.com', 'vimeo.com', 'twitch.tv',
]

MODE_Q = {
    "Phone": ["144p", "240p", "360p", "480p", "720p HD", "1080p FHD"],
    "TV":    ["144p", "240p", "360p", "480p", "720p HD"],
    "Music": ["Best Quality", "Medium", "Low Size"],
}

H_MAP = {
    "144p": "144", "240p": "240", "360p": "360",
    "480p": "480", "720p HD": "720", "1080p FHD": "1080",
}

# startup status messages shown one by one
STARTUP_MSGS = [
    ("[color=#a8ff78]ready. paste a url and press download.[/color]", 0.5),
    ("[color=#ffb347]tip: please turn on vpn before downloading.[/color]", 1.5),
    ("[color=#ff4d4d]note: if download fails, turn on vpn and try again.[/color]", 3.0),
]


class SilentLogger:
    def debug(self, m):   pass
    def info(self, m):    pass
    def warning(self, m): pass
    def error(self, m):   pass


def draw_rect(widget, rgba):
    with widget.canvas.before:
        c = Color(*rgba)
        r = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos =lambda *a: setattr(r, 'pos',  widget.pos))
    widget.bind(size=lambda *a: setattr(r, 'size', widget.size))
    return c


def mk_label(text, fsize=13, color=(0.9, 0.9, 0.9, 1),
             h=28, halign='left', markup=False):
    l = Label(
        text=text, markup=markup,
        font_size=dp(fsize), color=color,
        halign=halign, valign='middle',
        size_hint_y=None, height=dp(h),
    )
    l.bind(size=lambda *a: setattr(l, 'text_size', (l.width, None)))
    return l


class CBtn(Button):
    """simple colored flat button - no animation to avoid crash."""
    def __init__(self, text='', rgba=(0.4, 0.4, 1, 1),
                 fsize=14, h=46, **kw):
        super().__init__(
            text=text,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size=dp(fsize),
            bold=True,
            size_hint_y=None,
            height=dp(h),
            **kw,
        )
        self._on  = rgba
        self._off = (0.2, 0.2, 0.3, 1)
        self._bc  = draw_rect(self, rgba)
        self.bind(disabled=self._toggle)

    def _toggle(self, *a):
        self._bc.rgba = self._off if self.disabled else self._on

    def set_col(self, rgba):
        self._on = rgba
        if not self.disabled:
            self._bc.rgba = rgba


class Sep(Widget):
    def __init__(self, **kw):
        super().__init__(size_hint_y=None, height=dp(1), **kw)
        draw_rect(self, (0.22, 0.22, 0.38, 1))


class MainUI(BoxLayout):
    def __init__(self, **kw):
        super().__init__(
            orientation='vertical',
            padding=[dp(12), dp(8), dp(12), dp(10)],
            spacing=dp(8),
            **kw,
        )
        draw_rect(self, (0.06, 0.05, 0.16, 1))
        self._mode     = "Phone"
        self._save_dir = APP_DIR
        self._cancel   = threading.Event()
        self._build()

    def _build(self):
        # title
        tb = BoxLayout(size_hint_y=None, height=dp(50))
        draw_rect(tb, (0.09, 0.08, 0.20, 1))
        tb.add_widget(mk_label(
            "[b]YT-DLP  Downloader[/b]",
            fsize=20, color=(0.6, 0.5, 1.0, 1),
            h=50, halign='center', markup=True))
        self.add_widget(tb)
        self.add_widget(Sep())

        # mode buttons
        self.add_widget(mk_label(
            "Download Type:", fsize=11,
            color=(0.55, 0.55, 0.65, 1), h=20))
        mg = GridLayout(cols=3, size_hint_y=None,
                        height=dp(44), spacing=dp(6))
        self._mb = {}
        for m in ("Phone", "TV", "Music"):
            b = CBtn(m, (0.12, 0.10, 0.25, 1), fsize=13, h=44)
            b.bind(on_press=lambda btn, mode=m: self._set_mode(mode))
            self._mb[m] = b
            mg.add_widget(b)
        self.add_widget(mg)

        # url input
        ub = BoxLayout(orientation='vertical', size_hint_y=None,
                       height=dp(90), padding=[dp(10), dp(6)], spacing=dp(5))
        draw_rect(ub, (0.10, 0.09, 0.22, 1))
        ub.add_widget(mk_label(
            "Video / Music URL:", fsize=11,
            color=(0.55, 0.55, 0.65, 1), h=18))
        ur = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.url_in = TextInput(
            hint_text="https://youtube.com/watch?v=...",
            multiline=False,
            background_normal='', background_active='',
            background_color=(0.06, 0.05, 0.16, 1),
            foreground_color=(0.95, 0.95, 0.95, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.5, 1.0, 1),
            font_size=dp(12),
            size_hint_y=None, height=dp(44),
            padding=[dp(10), dp(10)],
        )
        self.url_in.bind(text=self._live_check)
        self._pb = CBtn("Paste", (0.00, 0.58, 0.52, 1), fsize=12, h=44)
        self._pb.size_hint_x = None
        self._pb.width = dp(64)
        self._pb.bind(on_press=self._paste)
        ur.add_widget(self.url_in)
        ur.add_widget(self._pb)
        ub.add_widget(ur)
        self.add_widget(ub)

        self._hint = mk_label("", fsize=11,
                              color=(1.0, 0.75, 0.20, 1), h=18)
        self.add_widget(self._hint)

        # folder row
        fr = BoxLayout(size_hint_y=None, height=dp(42),
                       spacing=dp(6), padding=[dp(8), dp(4)])
        draw_rect(fr, (0.10, 0.09, 0.22, 1))

        self._dir_input = TextInput(
            text=self._save_dir,
            hint_text="/storage/emulated/0/Download",
            multiline=False,
            background_normal='', background_active='',
            background_color=(0.06, 0.05, 0.16, 1),
            foreground_color=(0.9, 0.9, 1.0, 1),
            hint_text_color=(0.5, 0.5, 0.6, 1),
            cursor_color=(0.6, 0.5, 1.0, 1),
            font_size=dp(11),
            size_hint_y=None, height=dp(42),
            padding=[dp(8), dp(10)],
        )
        self._dir_input.bind(text=self._on_dir_change)

        set_btn = CBtn("Set", (0.60, 0.38, 0.00, 1), fsize=12, h=42)
        set_btn.size_hint_x = None
        set_btn.width = dp(50)
        set_btn.bind(on_press=self._set_dir)

        mk_btn = CBtn("Mk", (0.00, 0.55, 0.45, 1), fsize=12, h=42)
        mk_btn.size_hint_x = None
        mk_btn.width = dp(42)
        mk_btn.bind(on_press=self._mkdir)

        fr.add_widget(self._dir_input)
        fr.add_widget(set_btn)
        fr.add_widget(mk_btn)
        self.add_widget(fr)

        self._dir_hint = mk_label("", fsize=10,
                                  color=(0.6, 0.9, 0.6, 1), h=16)
        self.add_widget(self._dir_hint)

        # quality
        qr = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        qr.add_widget(mk_label(
            "Quality:", fsize=12,
            color=(0.55, 0.55, 0.65, 1), h=42))
        self._qual = Spinner(
            text="720p HD",
            values=MODE_Q["Phone"],
            background_normal='',
            background_color=(0.10, 0.09, 0.22, 1),
            color=(0.95, 0.95, 0.95, 1),
            font_size=dp(13),
            size_hint_y=None, height=dp(42),
        )
        qr.add_widget(self._qual)
        self.add_widget(qr)

        # download button
        self._dl = CBtn("Download", (0.42, 0.38, 1.00, 1),
                        fsize=16, h=54)
        self._dl.bind(on_press=self._start)
        self.add_widget(self._dl)

        # cancel button
        self._cx = CBtn("Cancel", (0.72, 0.10, 0.10, 1), fsize=14, h=42)
        self._cx.disabled = True
        self._cx.bind(on_press=self._cancel_dl)
        self.add_widget(self._cx)

        self.add_widget(Sep())

        self.add_widget(mk_label(
            "Status:", fsize=11,
            color=(0.55, 0.55, 0.65, 1), h=20))

        sv = ScrollView(size_hint=(1, 1))
        self._log = Label(
            text="",
            markup=True,
            color=(0.20, 0.85, 0.45, 1),
            font_size=dp(12),
            size_hint_y=None,
            halign='left', valign='top',
            padding=(dp(4), dp(4)),
        )
        self._log.bind(
            width=lambda *a: setattr(
                self._log, 'text_size', (self._log.width, None)),
            texture_size=lambda *a: setattr(
                self._log, 'height', self._log.texture_size[1]),
        )
        sv.add_widget(self._log)
        self.add_widget(sv)

        self._set_mode("Phone")

        # show startup messages with delay
        for msg, delay in STARTUP_MSGS:
            Clock.schedule_once(lambda dt, m=msg: self._append(m), delay)

    # ── helpers ──────────────────────────────────────

    def _append(self, line):
        if self._log.text == "":
            self._log.text = line
        else:
            self._log.text += "\n" + line

    def _clip(self, p):
        return ("..." + p[-30:]) if len(p) > 32 else p

    def _set_mode(self, mode):
        self._mode = mode
        for m, b in self._mb.items():
            b.set_col((0.42, 0.38, 1.00, 1) if m == mode
                      else (0.12, 0.10, 0.25, 1))
        self._qual.values = MODE_Q[mode]
        self._qual.text   = MODE_Q[mode][4 if mode != "Music" else 0]

    def _on_dir_change(self, *a):
        self._dir_hint.text = ""

    def _set_dir(self, *a):
        path = self._dir_input.text.strip()
        if not path:
            self._dir_hint.color = (1, 0.4, 0.4, 1)
            self._dir_hint.text  = "path is empty!"
            return
        if os.path.isdir(path):
            self._save_dir = path
            self._dir_hint.color = (0.4, 1, 0.6, 1)
            self._dir_hint.text  = "set! " + self._clip(path)
        else:
            self._dir_hint.color = (1, 0.75, 0.2, 1)
            self._dir_hint.text  = "folder does not exist. use mk to create it."

    def _mkdir(self, *a):
        path = self._dir_input.text.strip()
        if not path:
            self._dir_hint.color = (1, 0.4, 0.4, 1)
            self._dir_hint.text  = "enter path first!"
            return
        try:
            os.makedirs(path, exist_ok=True)
            self._save_dir = path
            self._dir_hint.color = (0.4, 1, 0.6, 1)
            self._dir_hint.text  = "folder created and set! " + self._clip(path)
        except Exception as e:
            self._dir_hint.color = (1, 0.4, 0.4, 1)
            self._dir_hint.text  = "error: " + str(e)[:50]

    def _live_check(self, *a):
        url = self.url_in.text.strip()
        if not url:
            self._hint.text = ""
            return
        ok, msg = self._validate(url)
        self._hint.color = (0.20, 0.85, 0.45, 1) if ok \
                           else (1.0, 0.75, 0.20, 1)
        self._hint.text  = msg

    def _validate(self, url):
        if not url:
            return False, "please enter a url first."
        if not re.match(r'^https?://', url, re.I):
            return False, "url must start with https://"
        if len(url) < 15:
            return False, "url is too short."
        if ' ' in url or '\n' in url or '\r' in url:
            return False, "url must not contain spaces or line breaks."
        if len(url) > 2000:
            return False, "url is too long."
        if not any(s in url.lower() for s in SUPPORTED):
            return False, "supported: youtube, instagram, facebook, tiktok..."
        return True, "url looks good!"

    def _paste(self, *a):
        try:
            from kivy.core.clipboard import Clipboard
            txt = Clipboard.paste()
            if txt:
                self.url_in.text = str(txt).strip()
            else:
                self._out("clipboard is empty.", warn=True)
        except Exception as e:
            self._out("paste error: " + str(e), err=True)

    def _lock(self, on):
        for w in (self._dl, self._pb, self.url_in, self._qual):
            w.disabled = on
        for b in self._mb.values():
            b.disabled = on
        self._cx.disabled = not on

    def _out(self, msg, err=False, warn=False, replace=False):
        hx = "#ff4d4d" if err else ("#ffb347" if warn else "#a8ff78")
        line = f"[color={hx}]{msg}[/color]"
        def _do(dt):
            if replace:
                self._log.text = line
            else:
                self._log.text += "\n" + line
        Clock.schedule_once(_do, 0)

    def _cancel_dl(self, *a):
        self._cancel.set()
        self._out("stopping download...", warn=True)

    # ── download ─────────────────────────────────────

    def _start(self, *a):
        url = self.url_in.text.strip()
        ok, msg = self._validate(url)
        if not ok:
            self._hint.color = (1.0, 0.3, 0.3, 1)
            self._hint.text  = msg
            self._out(msg, err=True, replace=True)
            return
        try:
            os.makedirs(self._save_dir, exist_ok=True)
        except Exception as e:
            self._out("folder error: " + str(e), err=True)
            return
        self._cancel.clear()
        self._lock(True)
        self._out("starting download...", replace=True)
        self._out("tip: make sure vpn is on if download fails.", warn=True)
        threading.Thread(
            target=self._worker, args=(url,), daemon=True).start()

    def _worker(self, url):
        try:
            import yt_dlp
        except ImportError:
            self._out("yt_dlp not found! install yt-dlp via pip.", err=True)
            Clock.schedule_once(lambda dt: self._lock(False), 0)
            return

        mode = self._mode
        qual = self._qual.text
        ev   = self._cancel

        def hook(d):
            if ev.is_set():
                raise Exception("__CANCELLED__")
            try:
                if d.get('status') == 'downloading':
                    pct   = str(d.get('_percent_str', '')).strip()
                    speed = str(d.get('_speed_str',   '')).strip()
                    eta   = str(d.get('_eta_str',     '')).strip()
                    if pct:
                        self._out(pct + "  " + speed + "  eta:" + eta)
                elif d.get('status') == 'finished':
                    self._out("saving file...", warn=True)
            except Exception:
                pass

        if mode == "Music":
            q = qual
            if q == "Low Size":
                fmt = "worst[ext=m4a]/worst[acodec!=none]/worst"
            elif q == "Medium":
                fmt = "best[ext=m4a][abr<=128]/best[acodec!=none]/best"
            else:
                fmt = "best[ext=m4a]/best[acodec!=none]/best"
            out = os.path.join(self._save_dir, "%(title)s.m4a")
        else:
            h   = H_MAP.get(qual, "720")
            fmt = (f"best[ext=mp4][height<={h}][acodec!=none]/"
                   f"best[ext=mp4][height<={h}]/"
                   f"best[ext=mp4]/best")
            out = os.path.join(self._save_dir, "%(title)s.%(ext)s")

        # android permission fix: use app dir for temp files
        tmp_dir = os.path.join(APP_DIR, "tmp")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except Exception:
            tmp_dir = self._save_dir

        opts = {
            "format":         fmt,
            "outtmpl":        out,
            "noplaylist":     True,
            "logger":         SilentLogger(),
            "progress_hooks": [hook],
            "socket_timeout": 30,
            "retries":        5,
            # android permission fix
            "cachedir":       False,
            "tmpfilename":    os.path.join(tmp_dir, "ytdlp_tmp"),
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 10; Mobile) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Mobile Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        try:
            if ev.is_set():
                self._out("download cancelled.", warn=True)
                Clock.schedule_once(lambda dt: self._lock(False), 0)
                return

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if ev.is_set():
                    self._out("download cancelled.", warn=True)
                    Clock.schedule_once(lambda dt: self._lock(False), 0)
                    return
                if info and isinstance(info, dict):
                    t = str(info.get('title', ''))[:55]
                    if t:
                        self._out("title: " + t)
                ydl.download([url])

            if not ev.is_set():
                self._out("download complete! saved to: " + self._save_dir)
            else:
                self._out("download cancelled.", warn=True)

        except Exception as e:
            s = str(e)
            if "__CANCELLED__" in s or ev.is_set():
                self._out("download cancelled.", warn=True)
            elif "403" in s:
                self._out("link expired. copy the url again.", err=True)
            elif "429" in s:
                self._out("too many requests. try again later.", err=True)
            elif "Permission denied" in s or "Errno 13" in s:
                self._out("permission denied. please turn on vpn and retry.", err=True)
            elif "unavailable" in s.lower():
                self._out("video is private or deleted.", err=True)
            elif "network" in s.lower() or "connect" in s.lower():
                self._out("network error. check internet or turn on vpn.", err=True)
            elif "Sign in" in s or "login" in s.lower():
                self._out("login required video. cannot download.", err=True)
            elif "format" in s.lower():
                self._out("format not found. try a different quality.", err=True)
            else:
                self._out("error: " + s[:150], err=True)
                self._out("tip: turn on vpn and try again.", warn=True)
        finally:
            Clock.schedule_once(lambda dt: self._lock(False), 0)


class YTApp(App):
    def build(self):
        self.title = "YT-DLP Downloader"
        return MainUI()


if __name__ == "__main__":
    YTApp().run()
