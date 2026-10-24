"""Clip Maker Pro - core engine (no GUI)."""
import os, re, csv, math, time, zipfile, subprocess, tempfile
import imageio_ffmpeg

import shutil


def _pick_ffmpeg():
    cands = []
    w = shutil.which("ffmpeg")
    if w:
        cands.append(w)
    cands.append(imageio_ffmpeg.get_ffmpeg_exe())
    for c in cands:
        try:
            o = subprocess.run([c, "-hide_banner", "-filters"], capture_output=True, text=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            if " subtitles " in o:
                return c, True
        except Exception:
            pass
    return cands[-1], False


FFMPEG, HAS_SUBS = _pick_ffmpeg()
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SIZES = {"short": (1080, 1920), "square": (1080, 1080), "wide": (1920, 1080)}
KSCALE = {"short": 1.0, "square": 0.8, "wide": 0.75}

DEFAULTS = {
    "out": "",
    "format_short": True, "format_square": False, "format_wide": False,
    "length": "170", "overlap": "0", "smart": True, "min_last": "15",
    "trim_start": "", "trim_end": "",
    "bg_mode": "Color", "bg_image": "", "bg_color": "#111111", "blur": "25",
    "crop": "1:1 Square", "crop_x": "0", "fit": "Fit", "vscale": "100", "voffset": "0",
    "logo": "", "logo_size": "12", "logo_pos": "Top-Right", "logo_opacity": "100",
    "progress": True, "progress_color": "#FF0000",
    "title": "", "title_color": "#FFFFFF", "title_size": "64", "title_y": "11",
    "font": "C:/Windows/Fonts/arialbd.ttf",
    "part_text": "Part {n}", "part_color": "#FFD400", "part_size": "56", "part_y": "83",
    "hook": "", "hook_sec": "3",
    "loudnorm": False,
    "captions": False, "cap_lang": "auto", "cap_model": "base", "cap_words": "4",
    "cap_size": "68", "cap_y": "22", "cap_font": "Arial",
    "encoder": "CPU (x264)", "quality": "20", "preset": "veryfast",
    "thumbs": True, "csv": True, "zip": False,
    "yt_title": "{title} | Part {n}", "yt_desc": "Full video dekhte channel visit koro!", "yt_tags": "",
}


class Cancelled(Exception):
    pass


def fnum(s, d):
    try:
        return float(str(s).strip())
    except Exception:
        return d


def parse_t(s):
    s = str(s).strip()
    if not s:
        return None
    t = 0.0
    for p in s.split(":"):
        t = t * 60 + float(p)
    return t


def hexc(c):
    c = str(c).strip().lstrip("#")
    return "0x" + (c if len(c) == 6 else "FFFFFF")


def esc(path):
    return path.replace("\\", "/").replace(":", "\\:")


def safe(name):
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "video"


def fmt_ts(x):
    x = max(0, x)
    h, r = divmod(x, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def plan(t0, t1, seg, overlap, cuts, min_last):
    """Return list of [start, end]. cuts = good cut points (silence middles)."""
    segs, s = [], t0
    while s < t1 - 1:
        target = s + seg
        if target >= t1:
            e = t1
        else:
            e = target
            near = [c for c in cuts if target - 12 <= c <= target and c > s + 20]
            if near:
                e = max(near)
        segs.append([s, e])
        if e >= t1:
            break
        s = max(e - overlap, s + 1)
    if len(segs) > 1 and (segs[-1][1] - segs[-1][0]) < min_last and (t1 - segs[-2][0]) <= 179:
        segs[-2][1] = t1
        segs.pop()
    return segs


def chunk_words(words, nmax):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= nmax or w[0] - cur[-1][1] > 0.8 or re.search(r"[.?!\u0964]$", cur[-1][2])):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [(c[0][0], c[-1][1], " ".join(x[2] for x in c)) for c in out]


def make_srt(lines, s, e):
    out, i = [], 1
    for a, b, t in lines:
        if b <= s or a >= e:
            continue
        out.append(f"{i}\n{fmt_ts(max(a, s) - s)} --> {fmt_ts(min(b, e) - s)}\n{t}\n")
        i += 1
    return "\n".join(out) or None


def text_png(path, text, font, size, color, maxw):
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype(font, size)
    except Exception:
        try:
            f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", size)
        except Exception:
            f = ImageFont.load_default(size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    sw = max(2, size // 18)
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            t = (cur + " " + word).strip()
            if cur and d.textlength(t, font=f) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = t
        lines.append(cur)
    txt = "\n".join(lines)
    box = d.multiline_textbbox((0, 0), txt, font=f, align="center", stroke_width=sw)
    pad = sw + 4
    im = Image.new("RGBA", (box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad), (0, 0, 0, 0))
    c = color.lstrip("#")
    rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) if len(c) == 6 else (255, 255, 255)
    ImageDraw.Draw(im).multiline_text((pad - box[0], pad - box[1]), txt, font=f, fill=rgb + (255,),
                                      align="center", stroke_width=sw, stroke_fill=(0, 0, 0, 255))
    im.save(path)
    return path


def build_cmd(S, video, start, dur, out, fk, n, total, tmp, enc, srt=None, preview_w=None):
    W, H = SIZES[fk]
    k = KSCALE[fk]
    mode = S["bg_mode"]
    if mode == "Image" and not S["bg_image"]:
        mode = "Color"
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostats"]
    nxt, bg_idx, logo_idx, prog_idx = 0, None, None, None
    if mode == "Image":
        cmd += ["-loop", "1", "-framerate", "30", "-i", S["bg_image"]]
        bg_idx = nxt; nxt += 1
    elif mode == "Color":
        cmd += ["-f", "lavfi", "-i", f"color=c={hexc(S['bg_color'])}:s={W}x{H}:r=30"]
        bg_idx = nxt; nxt += 1
    cmd += ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", video]
    vid = nxt; nxt += 1
    if S["logo"]:
        cmd += ["-i", S["logo"]]
        logo_idx = nxt; nxt += 1
    bh = max(6, int(14 * k))
    if S["progress"] and not preview_w:
        cmd += ["-f", "lavfi", "-i", f"color=c={hexc(S['progress_color'])}:s={W}x{bh}:r=30"]
        prog_idx = nxt; nxt += 1

    fc = []
    # video timestamp 0 theke shuru + fixed fps, jate shuru te background-only frame na ashe
    fc.append(f"[{vid}:v]setpts=PTS-STARTPTS,fps=30[v0]")
    if mode == "Blur":
        bl = int(fnum(S["blur"], 25))
        fc.append("[v0]split=2[va][vb]")
        fc.append(f"[va]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"boxblur={bl}:2,eq=brightness=-0.08,setsar=1[bg]")
        src = "[vb]"
    else:
        fc.append(f"[{bg_idx}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[bg]")
        src = "[v0]"
    # crop step: pan = -100 (left) .. 100 (right)
    pan = (fnum(S["crop_x"], 0) + 100) / 200
    pan = min(1, max(0, pan))
    cm = S["crop"]
    if cm.startswith("1:1"):
        fc.append(f"{src}crop=min(iw\\,ih):min(iw\\,ih):(iw-ow)*{pan:.3f}:(ih-oh)*0.5,setsar=1[cr]")
        src = "[cr]"
    elif cm.startswith("Full"):
        fc.append(f"{src}crop='min(iw\\,ih*{W}/{H})':'min(ih\\,iw*{H}/{W})':(iw-ow)*{pan:.3f}:(ih-oh)*0.5,setsar=1[cr]")
        src = "[cr]"
    if cm.startswith("Full") or (cm == "Original" and S["fit"] == "Fill"):
        fc.append(f"{src}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[vv]")
    else:
        pct = fnum(S["vscale"], 100) / 100
        tw, th = int(W * pct) // 2 * 2, int(H * pct) // 2 * 2
        fc.append(f"{src}scale={tw}:{th}:force_original_aspect_ratio=decrease,setsar=1[vv]")
    yoff = int(fnum(S["voffset"], 0))
    fc.append(f"[bg][vv]overlay=(W-w)/2:(H-h)/2+({yoff}):shortest=1[o1]")
    last = "o1"

    if logo_idx is not None:
        ls = int(W * fnum(S["logo_size"], 12) / 100) // 2 * 2
        op = fnum(S["logo_opacity"], 100) / 100
        pos = {"Top-Right": "W-w-40:40", "Top-Left": "40:40",
               "Bottom-Right": "W-w-40:H-h-40", "Bottom-Left": "40:H-h-40"}[S["logo_pos"]]
        fc.append(f"[{logo_idx}:v]scale={ls}:-1,format=rgba,colorchannelmixer=aa={op}[lg]")
        fc.append(f"[{last}][lg]overlay={pos}[o2]")
        last = "o2"
    if prog_idx is not None:
        fc.append(f"[{last}][{prog_idx}:v]overlay=x='-w+w*t/{dur:.3f}':y=H-h:shortest=1[o3]")
        last = "o3"

    font = S["font"]
    if fk == "short":
        ty, py = int(H * fnum(S["title_y"], 11) / 100), int(H * fnum(S["part_y"], 83) / 100)
        hy, capm = int(H * 0.20), int(H * fnum(S["cap_y"], 22) / 100)
    elif fk == "square":
        ty, py, hy, capm = int(H * 0.07), int(H * 0.84), int(H * 0.15), int(H * 0.20)
    else:
        ty, py, hy, capm = int(H * 0.04), int(H * 0.90), int(H * 0.12), int(H * 0.08)

    def tok(t):
        return (t.replace("{n}", str(n)).replace("{total}", str(total)).replace("\\n", "\n"))

    filters = []
    if srt and not preview_w:
        with open(os.path.join(tmp, "sub.srt"), "w", encoding="utf-8") as f:
            f.write(srt)
        cf = S["cap_font"]
        if S["cap_lang"] == "bn" and cf == "Arial":
            cf = "Nirmala UI"
        csz = int(fnum(S["cap_size"], 68) * k)
        filters.append(f"subtitles=sub.srt:original_size={W}x{H}:force_style='FontName={cf},FontSize={csz},"
                       f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=0,"
                       f"Bold=1,Alignment=2,MarginV={capm}'")
    if filters:
        fc.append(f"[{last}]" + ",".join(filters) + "[o4]")
        last = "o4"
        filters = []

    texts = []
    for name, text, size, color, y, en in (
            ("t", S["title"], fnum(S["title_size"], 64), S["title_color"], ty, ""),
            ("p", S["part_text"], fnum(S["part_size"], 56), S["part_color"], py, ""),
            ("h", S["hook"], 72, "#FFFFFF", hy, f":enable='between(t,0,{fnum(S['hook_sec'], 3)})'")):
        text = tok(text)
        if text.strip():
            png = text_png(os.path.join(tmp, name + ".png"), text, font, int(size * k), color, int(W * 0.9))
            texts.append((png, y, en))
    for i, (png, y, en) in enumerate(texts):
        cmd += ["-i", png]
        idx = nxt
        nxt += 1
        fc.append(f"[{last}][{idx}:v]overlay=x=(W-w)/2:y={y}{en}[ot{i}]")
        last = f"ot{i}"
    if preview_w:
        filters.append(f"scale={preview_w}:-2")
    fc.append(f"[{last}]" + (",".join(filters) if filters else "null") + "[out]")

    cmd += ["-filter_complex", ";".join(fc), "-map", "[out]"]
    if preview_w:
        cmd += ["-frames:v", "1", "-an", out]
        return cmd
    cmd += ["-map", f"{vid}:a?"]
    q = str(int(fnum(S["quality"], 20)))
    if enc.startswith("NVIDIA"):
        cmd += ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", q, "-b:v", "0"]
    else:
        cmd += ["-c:v", "libx264", "-preset", S["preset"], "-crf", q]
    cmd += ["-pix_fmt", "yuv420p", "-r", "30"]
    af = "aresample=async=1:first_pts=0"
    if S["loudnorm"]:
        af += ",loudnorm=I=-16:TP=-1.5:LRA=11"
    cmd += ["-af", af]
    cmd += ["-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", out]
    return cmd


class Engine:
    def __init__(self, status_cb=lambda t, p=None: None):
        self.status = status_cb
        self.proc = None
        self.cancel = False

    def stop(self):
        self.cancel = True
        if self.proc and self.proc.poll() is None:
            self.proc.kill()

    def ff(self, cmd, cwd=None):
        self.proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                     text=True, encoding="utf-8", errors="replace", creationflags=NOWIN)
        _, err = self.proc.communicate()
        if self.cancel:
            raise Cancelled()
        return self.proc.returncode, err

    def duration(self, path):
        p = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=NOWIN)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", p.stderr)
        if not m:
            raise RuntimeError("Video duration pawa jaye nai: " + path)
        h, mi, s = m.groups()
        return int(h) * 3600 + int(mi) * 60 + float(s)

    def find_cuts(self, video):
        rc, err = self.ff([FFMPEG, "-hide_banner", "-nostats", "-i", video, "-vn", "-af",
                           "silencedetect=noise=-32dB:d=0.35", "-f", "null", "-"])
        cuts, st = [], None
        for line in err.splitlines():
            m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
            if m:
                st = float(m.group(1))
            m = re.search(r"silence_end:\s*([\d.]+)", line)
            if m and st is not None:
                cuts.append((max(st, 0) + float(m.group(1))) / 2)
                st = None
        return cuts

    def transcribe(self, video, lang, model_size, tmp, nwords):
        from faster_whisper import WhisperModel
        wav = os.path.join(tmp, "a.wav")
        self.status("Audio ber korchi...")
        self.ff([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-vn", "-ac", "1",
                 "-ar", "16000", wav])
        self.status(f"Whisper model load hochche ({model_size}), prothombar download hote pare...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segs, info = model.transcribe(wav, language=None if lang == "auto" else lang,
                                      word_timestamps=True, vad_filter=True)
        words = []
        for sg in segs:
            if self.cancel:
                raise Cancelled()
            self.status(f"Captions: {sg.end / max(info.duration, 1) * 100:.0f}% ...")
            for w in (sg.words or []):
                words.append((w.start, w.end, w.word.strip()))
        return chunk_words(words, nwords)

    def preview(self, S, video, fk, out_png, width):
        tmp = tempfile.mkdtemp()
        total = self.duration(video)
        t = total * 0.3
        cmd = build_cmd(S, video, t, 2, out_png, fk, 1, 5, tmp, "CPU", preview_w=width)
        rc, err = self.ff(cmd, tmp)
        if rc != 0:
            raise RuntimeError(err[-900:])

    def run(self, S, videos, outdir):
        self.cancel = False
        tmp = tempfile.mkdtemp()
        formats = [f for f in ("short", "square", "wide") if S["format_" + f]]
        seg = max(10, fnum(S["length"], 170))
        if "short" in formats and seg > 179:
            seg = 179
        overlap = max(0, fnum(S["overlap"], 0))
        if S["captions"] and not HAS_SUBS:
            raise RuntimeError("Captions er jonno ffmpeg e 'subtitles' filter lagbe. CMD e likho: "
                               "winget install Gyan.FFmpeg  (tarpor tool restart koro)")
        plans = []
        for v in videos:
            self.status("Video check korchi: " + os.path.basename(v))
            total = self.duration(v)
            t0 = parse_t(S["trim_start"]) or 0
            t1 = min(parse_t(S["trim_end"]) or total, total)
            cuts = []
            if S["smart"]:
                self.status("Silence khujchi (smart cut)...")
                cuts = self.find_cuts(v)
            lines = None
            if S["captions"]:
                lines = self.transcribe(v, S["cap_lang"], S["cap_model"], tmp, int(fnum(S["cap_words"], 4)))
            plans.append((v, plan(t0, t1, seg, overlap, cuts, fnum(S["min_last"], 15)), lines))
        jobs = sum(len(p[1]) for p in plans) * len(formats)
        done, t_start, enc = 0, time.time(), S["encoder"]
        for v, segs, lines in plans:
            vname = safe(os.path.splitext(os.path.basename(v))[0])
            folder = os.path.join(outdir, vname + "_clips")
            os.makedirs(folder, exist_ok=True)
            rows, made = [], []
            for n, (s, e) in enumerate(segs, 1):
                for fk in formats:
                    fname = f"{vname}_Part{n:02d}_{fk}.mp4"
                    outp = os.path.join(folder, fname)
                    el = time.time() - t_start
                    eta = f" | ETA {int(el / done * (jobs - done) // 60)} min" if done else ""
                    self.status(f"Clip {done + 1}/{jobs}: Part {n} ({fk}){eta}", done / jobs * 100)
                    srt = make_srt(lines, s, e) if lines else None
                    cmd = build_cmd(S, v, s, e - s, outp, fk, n, len(segs), tmp, enc, srt)
                    rc, err = self.ff(cmd, tmp)
                    if rc != 0 and enc.startswith("NVIDIA"):
                        enc = "CPU"
                        cmd = build_cmd(S, v, s, e - s, outp, fk, n, len(segs), tmp, enc, srt)
                        rc, err = self.ff(cmd, tmp)
                    if rc != 0:
                        raise RuntimeError(err[-900:])
                    made.append(outp)
                    if S["thumbs"]:
                        self.ff([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "1", "-i", outp,
                                 "-frames:v", "1", "-q:v", "2", outp[:-4] + ".jpg"])
                    ttl = (S["title"] or vname)
                    rows.append([fname,
                                 S["yt_title"].replace("{title}", ttl).replace("{n}", str(n)).replace("{total}", str(len(segs))),
                                 S["yt_desc"].replace("{n}", str(n)), S["yt_tags"], f"{int(s // 60)}:{int(s % 60):02d}"])
                    done += 1
            if S["csv"]:
                with open(os.path.join(folder, "upload_list.csv"), "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["file", "youtube_title", "description", "tags", "start_in_original"])
                    w.writerows(rows)
            if S["zip"]:
                self.status("ZIP banacchi...")
                with zipfile.ZipFile(os.path.join(outdir, vname + "_clips.zip"), "w", zipfile.ZIP_STORED) as z:
                    for fp in made:
                        z.write(fp, os.path.basename(fp))
        self.status(f"Hoye gese! {jobs} ta clip toiri", 100)
        return folder
