@echo off
title Clip Maker Pro setup
python -m pip install --upgrade imageio-ffmpeg pillow
echo.
echo (Optional) Auto caption er jonno faster-whisper install hochche. Fail hole problem nai.
python -m pip install faster-whisper
echo.
python clipmaker.py
pause
