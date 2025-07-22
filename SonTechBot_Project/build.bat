@echo off
echo.
echo [INFO] SonTechBot Nuitka derleyici baslatiliyor...
echo [INFO] Bu islem bilgisayarinizin performansina gore uzun surebilir.
echo.

REM Derleme icin gecici klasorleri temizle
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q sontechbot_gui.exe.onefile-build-dir

echo [INFO] Derleme basliyor...

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-disable-console ^
    --windows-icon-from-ico="logo.ico" ^
    --plugin-enable=kivy ^
    --plugin-enable=tk-inter ^
    --include-data-dir=sontechbot=sontechbot ^
    --output-dir=dist ^
    sontechbot_gui.py

echo.
echo [SUCCESS] Derleme tamamlandi!
echo [SUCCESS] Calistirilabilir dosyaniz 'dist' klasorunun icinde.
echo.
pause