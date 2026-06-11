@echo off
echo ============================================================
echo  Abrindo Chrome com Remote Debugging na porta 9222
echo ============================================================
echo.
echo  PROXIMOS PASSOS:
echo   1. Conecte a VPN
echo   2. Faca o SSO manualmente nesta janela do Chrome
echo   3. Execute rodar.bat
echo.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="C:\eplus_profile"

echo  Chrome iniciado. Esta janela pode ser fechada.
pause
