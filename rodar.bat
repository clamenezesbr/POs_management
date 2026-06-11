@echo off
echo ============================================================
echo  eplus.huawei.com - Automacao Deal Registration
echo ============================================================
echo.
echo  Pre-requisitos:
echo   [x] launch_chrome.bat executado
echo   [x] VPN conectada
echo   [x] SSO feito manualmente no Chrome
echo.

python main.py

echo.
echo  Pressione qualquer tecla para fechar...
pause >nul
