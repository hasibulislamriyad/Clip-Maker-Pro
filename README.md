# Clip Maker Pro

Turn one long video (for example a 1 hour drama or podcast) into many ready-to-upload clips, each placed inside your own template. Built for YouTube Shorts, but it also exports square (1:1) and normal (16:9) versions.

Runs fully on your own Windows PC. No upload, no account, no watermark.

## What it does

1. You add a long video (or many videos).
2. It cuts the video into 2 to 3 minute parts (default 2:50).
3. Every part is placed inside your template: background, title, "Part 1, Part 2...", logo, hook text, progress bar, captions.
4. You get finished `.mp4` files, thumbnails and a CSV with titles/descriptions. You upload them to YouTube yourself.

## Features

**Cutting**
- Custom clip length (Shorts max is 3 min, so it is capped at 179 sec for Shorts)
- **Smart cut ON/OFF**: ON cuts at silence so sentences and scenes are not broken in the middle, OFF cuts at exact intervals
- Overlap between clips
- Trim start / end (process only a part of the video)
- Tiny last clip is merged into the previous one
- Batch: add many videos at once

**Template**
- Background: solid color, your own image, or blurred copy of the video
- Video crop: **1:1 Square** (big square video in the middle of a 9:16 frame), **Full frame 9:16**, or Original 16:9
- Crop position slider (left / center / right) to choose which part of the picture stays
- Video size and up/down position
- Logo / watermark with size, corner and opacity
- Progress bar that fills while the clip plays
- Live **Preview** button before you render
- Save / load templates as JSON, last settings are remembered

**Text**
- Title, "Part {n}/{total}" text, colors, sizes, positions, custom font
- Hook text shown in the first few seconds

**Captions and audio**
- Auto captions with Whisper AI (Bangla, English, Hindi and more), burned into the video
- Volume normalize so every clip has the same loudness

**Output**
- Formats: Shorts 9:16, Square 1:1, Normal 16:9 (pick one or all)
- CPU (x264) or NVIDIA GPU (nvenc) encoding, auto fallback to CPU
- Thumbnail `.jpg` for each clip
- `upload_list.csv` with YouTube title, description and tags for each clip
- Optional ZIP of all clips
- Progress, ETA and Cancel button

## Requirements

- Windows 10 or 11
- [Python 3.9+](https://www.python.org/downloads/) (tick **Add Python to PATH** during install)
- Internet only for the first setup (and first caption model download)

FFmpeg is installed automatically through the `imageio-ffmpeg` package. You do not need to install it by hand.

## Install and run

```bash
git clone https://github.com/hasibulislamriyad/Clip-Maker-Pro.git
cd Clip-Maker-Pro
```

Then double click **`RUN.bat`**. It installs the needed packages and opens the app.

Or manually:

```bash
pip install -r requirements.txt
python clipmaker.py
```

If you do not need auto captions you can remove `faster-whisper` from `requirements.txt`; everything else still works.

## How to use

1. **Video tab**: click **Add** and choose your video(s). Choose a **Save folder**. Tick the formats you want. Set clip length (170 = 2:50) and smart cut on/off.
2. **Template tab**: choose background (Color / Image / Blur), video crop (1:1 Square is a good start), logo, progress bar.
3. **Text tab**: write your title, set the Part text, optional hook text.
4. Click **Preview dekho** to see how a clip will look. Change settings until you like it.
5. Optional: save the look with **Template save** so you can reuse it.
6. Click **CLIP BANAO**. When done, the output folder opens by itself.

Tip: test with a 2 to 3 minute video first, then run your full video.

## Output

For a video called `drama.mp4` you get:

```
drama_clips/
  drama_Part01_short.mp4
  drama_Part01_short.jpg
  drama_Part02_short.mp4
  ...
  upload_list.csv
```

`upload_list.csv` contains the file name, YouTube title, description, tags and the start time of that part in the original video. Open it in Excel and copy-paste while uploading.

In the Text tab you can use `{n}` for the part number and `{total}` for the number of parts. Use `\n` for a new line.

## Settings overview

| Setting | Meaning |
|---|---|
| Clip length | Seconds per clip. 170 = 2:50 |
| Smart cut | Cut at silence instead of exact seconds |
| Overlap | Seconds repeated at the start of the next clip |
| Video crop | Original, 1:1 Square, Full frame (9:16) |
| Crop position | -100 left, 0 center, 100 right |
| Background | Color, Image or Blur |
| Quality (CRF) | Lower is better quality and bigger file. 18 to 23 is good |
| Speed | ultrafast is quick, slow is smaller files |

Your last settings are saved in `clipmaker_settings.json` in your user folder.

## Troubleshooting

**`python` is not recognized**: reinstall Python and tick *Add Python to PATH*.

**Captions error about the "subtitles" filter**: your FFmpeg build has no subtitle support. Open CMD and run `winget install Gyan.FFmpeg`, then restart the app.

**Captions are slow the first time**: the Whisper model is downloaded once. Use the `tiny` or `base` model for speed, `small` or `medium` for better accuracy.

**Bangla title looks broken**: joined letters can break in some fonts. Use an English or Banglish title, or choose `Nirmala.ttf` as font. For Bangla captions choose Language `bn` and font name `Nirmala UI`.

**NVIDIA GPU encoding fails**: the app switches to CPU automatically.

**Rendering is slow**: every clip is re-encoded. Use the `ultrafast` or `veryfast` speed, or NVIDIA encoding if you have a supported GPU.

## Important note about content

Only use videos you own or have permission to use. Re-uploading other people's dramas, movies or shows can cause copyright claims or strikes on YouTube.

---

## বাংলায় সংক্ষেপে

1. Python install করুন (Add Python to PATH টিক দিতে ভুলবেন না)।
2. এই repo download করে `RUN.bat` এ double click করুন।
3. **Video** tab এ ভিডিও আর Save folder দিন।
4. **Template** আর **Text** tab এ আপনার পছন্দমতো background, title, logo দিন।
5. **Preview** দেখে **CLIP BANAO** চাপুন।
6. তৈরি হওয়া ক্লিপগুলো folder থেকে নিয়ে YouTube এ upload করুন। Title/description এর জন্য `upload_list.csv` ব্যবহার করুন।
