@echo off
chcp 65001 >nul
cd /d "%~dp0"
schtasks /Delete /TN "KMOUSeungsunNoticeEvery5Min" /F
schtasks /Delete /TN "KMOUSeungsunNoticeHourly" /F
schtasks /Delete /TN "KMOUSeungsunNoticeOnLogon" /F
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KMOUSeungsunNotice.bat" 2>nul
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KMOUSeungsunNotice.lnk" 2>nul
echo.
echo 자동 시작 예약 작업을 삭제했습니다.
pause
