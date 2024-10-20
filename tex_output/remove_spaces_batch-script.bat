@echo off
setlocal enabledelayedexpansion

set "folder=%cd%"

for /f "delims=" %%F in ('dir /b /a-d "%folder%"') do (
    set "oldname=%%F"
    set "newname=!oldname: =_!"
    if not "!oldname!"=="!newname!" (
        ren "%folder%\!oldname!" "!newname!"
        echo Renamed: !oldname! to !newname!
    )
)

echo Done.
pause
