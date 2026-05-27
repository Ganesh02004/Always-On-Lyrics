@echo off
title Install Always-On Lyrics Overlay
cls
echo ==================================================
echo   Starting Always-On Lyrics Overlay Installer...
echo ==================================================
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
