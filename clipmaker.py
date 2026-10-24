"""Clip Maker Pro - GUI"""
import os, json, threading, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import core
from core import DEFAULTS, Engine, Cancelled

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), "clipmaker_settings.json")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clip Maker Pro")
        self.geometry("1040x720")
        self.V = {}
        for k, v in DEFAULTS.items():
            self.V[k] = tk.BooleanVar(value=v) if isinstance(v, bool) else tk.StringVar(value=v)
        self.videos = []
        self.engine = None
        self.prev_img = None
        self.load_settings(SETTINGS_FILE)
        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- settings ----------
    def get(self):
        return {k: v.get() for k, v in self.V.items()}

    def load_settings(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self.V:
                    self.V[k].set(v)
        except Exception:
            pass

    def save_settings(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.get(), f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def on_close(self):
        self.save_settings(SETTINGS_FILE)
        if self.engine:
            self.engine.stop()
        self.destroy()

    def save_template(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Template", "*.json")])
        if p:
            self.save_settings(p)

    def load_template(self):
        p = filedialog.askopenfilename(filetypes=[("Template", "*.json")])
        if p:
            self.load_settings(p)

    # ---------- ui helpers ----------
    def browse(self, key, kind):
        if kind == "img":
            p = filedialog.askopenfilename(filetypes=[("Image", "*.png *.jpg *.jpeg *.webp")])
        elif kind == "font":
            p = filedialog.askopenfilename(initialdir="C:/Windows/Fonts", filetypes=[("Font", "*.ttf *.otf")])
        else:
            p = filedialog.askdirectory()
        if p:
            self.V[key].set(p)

    def pick_color(self, key):
        c = colorchooser.askcolor(color=self.V[key].get())[1]
        if c:
            self.V[key].set(c.upper())

    def E(self, p, r, label, key, browse=None, color=False, width=30):
        ttk.Label(p, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=3)
        ttk.Entry(p, textvariable=self.V[key], width=width).grid(row=r, column=1, sticky="we", pady=3)
        if browse:
            ttk.Button(p, text="Browse", width=8, command=lambda: self.browse(key, browse)).grid(row=r, column=2, padx=4)
        if color:
            ttk.Button(p, text="Color", width=8, command=lambda: self.pick_color(key)).grid(row=r, column=2, padx=4)

    def C(self, p, r, label, key):
        ttk.Checkbutton(p, text=label, variable=self.V[key]).grid(row=r, column=0, columnspan=3, sticky="w", padx=6, pady=3)

    def D(self, p, r, label, key, values):
        ttk.Label(p, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=3)
        ttk.Combobox(p, textvariable=self.V[key], values=values, state="readonly", width=27).grid(row=r, column=1, sticky="w", pady=3)

    def note(self, p, r, text):
        ttk.Label(p, text=text, foreground="#666").grid(row=r, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 2))

    # ---------- ui ----------
    def build_ui(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        right = ttk.Frame(self, width=330)
        right.pack(side="right", fill="y", padx=8, pady=8)

        nb = ttk.Notebook(left)
        nb.pack(fill="both", expand=True)
        tabs = {}
        for name in ("Video", "Template", "Text", "Captions/Audio", "Output"):
            f = ttk.Frame(nb)
            f.columnconfigure(1, weight=1)
            nb.add(f, text=name)
            tabs[name] = f

        # --- Video tab
        t = tabs["Video"]
        ttk.Label(t, text="Video list (ek sathe onek video dite paro)").grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=3)
        self.lb = tk.Listbox(t, height=6, selectmode="extended")
        self.lb.grid(row=1, column=0, columnspan=2, sticky="we", padx=6)
        bf = ttk.Frame(t)
        bf.grid(row=1, column=2, sticky="n", padx=4)
        ttk.Button(bf, text="Add", width=8, command=self.add_videos).pack(pady=1)
        ttk.Button(bf, text="Remove", width=8, command=self.remove_videos).pack(pady=1)
        ttk.Button(bf, text="Clear", width=8, command=self.clear_videos).pack(pady=1)
        self.E(t, 2, "Save folder", "out", browse="dir")
        self.note(t, 3, "Format (ja ja chao tick koro)")
        ff = ttk.Frame(t)
        ff.grid(row=4, column=0, columnspan=3, sticky="w")
        for lab, key in (("Shorts 9:16", "format_short"), ("Square 1:1", "format_square"), ("Normal 16:9", "format_wide")):
            ttk.Checkbutton(ff, text=lab, variable=self.V[key]).pack(side="left", padx=6)
        self.note(t, 5, "Cutting")
        self.E(t, 6, "Clip length (sec)", "length")
        self.E(t, 7, "Overlap (sec)", "overlap")
        self.C(t, 8, "Smart cut ON/OFF (ON = silence e kato, OFF = thik 2:50 por por kato)", "smart")
        self.E(t, 9, "Last clip choto hole merge (sec)", "min_last")
        self.E(t, 10, "Trim start (mm:ss)", "trim_start")
        self.E(t, 11, "Trim end (mm:ss)", "trim_end")
        self.note(t, 12, "Shorts max 3 min, tai Shorts e 179 sec er beshi hole auto 179 hobe.")

        # --- Template tab
        t = tabs["Template"]
        self.D(t, 0, "Background", "bg_mode", ["Color", "Image", "Blur"])
        self.E(t, 1, "Background image", "bg_image", browse="img")
        self.E(t, 2, "Background color", "bg_color", color=True)
        self.E(t, 3, "Blur strength (Blur mode)", "blur")
        self.D(t, 4, "Video crop", "crop", ["Original", "1:1 Square", "Full frame (9:16)"])
        self.E(t, 5, "Crop position (-100 bam ... 100 dan)", "crop_x")
        self.D(t, 6, "Video fit (Original e)", "fit", ["Fit", "Fill"])
        self.E(t, 7, "Video size %", "vscale")
        self.E(t, 8, "Video up/down (px)", "voffset")
        self.note(t, 9, "Logo / watermark")
        self.E(t, 10, "Logo image", "logo", browse="img")
        self.E(t, 11, "Logo size %", "logo_size")
        self.D(t, 12, "Logo position", "logo_pos", ["Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left"])
        self.E(t, 13, "Logo opacity %", "logo_opacity")
        self.C(t, 14, "Niche progress bar dekhao", "progress")
        self.E(t, 15, "Progress bar color", "progress_color", color=True)

        # --- Text tab
        t = tabs["Text"]
        self.E(t, 0, "Title (upore)", "title")
        self.E(t, 1, "Title color", "title_color", color=True)
        self.E(t, 2, "Title size", "title_size")
        self.E(t, 3, "Title position % (Shorts)", "title_y")
        self.E(t, 4, "Part text", "part_text")
        self.E(t, 5, "Part color", "part_color", color=True)
        self.E(t, 6, "Part size", "part_size")
        self.E(t, 7, "Part position % (Shorts)", "part_y")
        self.E(t, 8, "Hook text (shuru te)", "hook")
        self.E(t, 9, "Hook koto sec", "hook_sec")
        self.E(t, 10, "Font file", "font", browse="font")
        self.note(t, 11, "Part text e {n} = part number, {total} = mot part. Notun line er jonno \\n likho.\n"
                         "English/Banglish title best. Bangla likhle Nirmala.ttf font dao, kichu jukto okkhor bhenge jete pare.")

        # --- Captions/Audio
        t = tabs["Captions/Audio"]
        self.C(t, 0, "Auto captions (Whisper AI, faster-whisper lagbe)", "captions")
        self.D(t, 1, "Language", "cap_lang", ["auto", "bn", "en", "hi", "ur"])
        self.D(t, 2, "Model", "cap_model", ["tiny", "base", "small", "medium"])
        self.E(t, 3, "Ek line e koyta word", "cap_words")
        self.E(t, 4, "Caption size", "cap_size")
        self.E(t, 5, "Caption position % (niche theke)", "cap_y")
        self.E(t, 6, "Caption font name", "cap_font")
        self.note(t, 7, "Bangla caption: Language = bn, font = Nirmala UI. Model jototuku boro, tototuku slow kintu valo.\n"
                        "Prothombar model download hobe (internet lagbe).")
        self.C(t, 8, "Audio volume normalize (sob clip e same sound)", "loudnorm")

        # --- Output
        t = tabs["Output"]
        self.D(t, 0, "Encoder", "encoder", ["CPU (x264)", "NVIDIA GPU (nvenc)"])
        self.E(t, 1, "Quality (CRF, kom = valo)", "quality")
        self.D(t, 2, "Speed", "preset", ["ultrafast", "veryfast", "fast", "medium", "slow"])
        self.C(t, 3, "Thumbnail (jpg) banao", "thumbs")
        self.C(t, 4, "YouTube upload list (CSV) banao", "csv")
        self.C(t, 5, "Sob clip ZIP kore dao", "zip")
        self.E(t, 6, "YouTube title", "yt_title")
        self.E(t, 7, "Description", "yt_desc")
        self.E(t, 8, "Tags (comma diye)", "yt_tags")
        self.note(t, 9, "NVIDIA GPU fail korle auto CPU te chole jabe.")

        # --- Right panel
        ttk.Label(right, text="Template Preview").pack()
        self.prev = tk.Label(right, bg="#222", width=40, height=24)
        self.prev.pack(pady=4)
        ttk.Button(right, text="Preview dekho", command=self.do_preview).pack(fill="x", pady=2)
        ttk.Button(right, text="Template save", command=self.save_template).pack(fill="x", pady=2)
        ttk.Button(right, text="Template load", command=self.load_template).pack(fill="x", pady=2)
        self.btn = ttk.Button(right, text="CLIP BANAO", command=self.start)
        self.btn.pack(fill="x", pady=(14, 2), ipady=6)
        self.cbtn = ttk.Button(right, text="Cancel", command=self.cancel, state="disabled")
        self.cbtn.pack(fill="x", pady=2)
        self.bar = ttk.Progressbar(right, length=300)
        self.bar.pack(pady=6)
        self.status = tk.Label(right, text="Ready", wraplength=300, justify="left")
        self.status.pack(fill="x")
        self.refresh_list()

    # ---------- video list ----------
    def refresh_list(self):
        self.lb.delete(0, "end")
        for v in self.videos:
            self.lb.insert("end", v)

    def add_videos(self):
        ps = filedialog.askopenfilenames(filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi *.webm *.flv")])
        for p in ps:
            if p not in self.videos:
                self.videos.append(p)
        self.refresh_list()

    def remove_videos(self):
        for i in reversed(self.lb.curselection()):
            del self.videos[i]
        self.refresh_list()

    def clear_videos(self):
        self.videos = []
        self.refresh_list()

    # ---------- actions ----------
    def set_status(self, text, val=None):
        def f():
            self.status.config(text=text)
            if val is not None:
                self.bar.config(value=val)
        self.after(0, f)

    def do_preview(self):
        if not self.videos:
            messagebox.showwarning("Video lagbe", "Age Video tab e ekta video add koro")
            return
        S = self.get()
        fk = "short" if S["format_short"] else ("square" if S["format_square"] else "wide")
        width = 420 if fk == "wide" else 300

        def work():
            try:
                png = os.path.join(tempfile.gettempdir(), "clipmaker_preview.png")
                Engine(self.set_status).preview(S, self.videos[0], fk, png, width)
                def show():
                    self.prev_img = tk.PhotoImage(file=png)
                    self.prev.config(image=self.prev_img, width=self.prev_img.width(), height=self.prev_img.height())
                self.after(0, show)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Preview error", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def start(self):
        S = self.get()
        if not self.videos or not S["out"]:
            messagebox.showwarning("Eita lagbe", "Video ar Save folder select koro")
            return
        if not (S["format_short"] or S["format_square"] or S["format_wide"]):
            messagebox.showwarning("Format", "Komporkhe ekta format tick koro")
            return
        self.save_settings(SETTINGS_FILE)
        self.engine = Engine(self.set_status)
        self.btn.config(state="disabled")
        self.cbtn.config(state="normal")

        def work():
            try:
                folder = self.engine.run(S, list(self.videos), S["out"])
                self.after(0, lambda: os.startfile(folder))
            except Cancelled:
                self.set_status("Cancel kora hoyeche")
            except Exception as e:
                self.set_status("Error hoyeche")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: (self.btn.config(state="normal"), self.cbtn.config(state="disabled")))
        threading.Thread(target=work, daemon=True).start()

    def cancel(self):
        if self.engine:
            self.engine.stop()


if __name__ == "__main__":
    App().mainloop()
