@echo off
chcp 65001 >nul
title Bich Trai Cay - Bang gia
echo ============================================
echo   BICH TRAI CAY - Bang gia trai cay
echo ============================================
echo.

REM Kiem tra Flask, neu chua co thi tu cai
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Dang cai Flask lan dau, vui long doi...
    python -m pip install Flask
    echo.
)

echo Dang khoi dong web... Mo trinh duyet va vao:  http://127.0.0.1:5000
echo Bam Ctrl+C trong cua so nay de tat web.
echo.
python app.py
pause
