@echo off
chcp 65001 > nul
title 紫微天機 - 啟動伺服器
echo 正在啟動紫微天機後端伺服器...
"C:\Users\ALBERT\.virtualenvs\FatePurple\Scripts\python.exe" app.py
pause
