@echo off
setlocal enabledelayedexpansion

REM ====================================================================
REM  make_raceline_video.bat
REM
REM  Renders an MP4 of a real telemetry lap played on the IDEAL racing line.
REM  Spatial path: IQP min-curvature line.
REM  Animation timing + speed readout: real telemetry CSV (REQUIRED).
REM
REM  USAGE:
REM    Double-click          -> renders Miami with VER's telemetry.
REM    Drag a *_outline.json onto this .bat -> renders that track
REM      (telemetry CSV is auto-resolved from the per-track table below;
REM       add new entries as needed).
REM    From cmd, override telemetry explicitly:
REM      make_raceline_video.bat path\to\track_outline.json --zoom 25 --fps 60
REM
REM  Output: <stem>_optimal_lap.mp4 next to this .bat.
REM ====================================================================

set "PYTHON=C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
set "SCRIPT=%~dp0raceline_video.py"
set "DEFAULT_OUTLINE=%~dp0F1_Pipeline_Assets\tracks\miami_grand_prix_outline.json"

set "OUTLINE=%~1"
if "%OUTLINE%"=="" set "OUTLINE=%DEFAULT_OUTLINE%"

if not exist "%PYTHON%" goto :err_py
if not exist "%SCRIPT%"  goto :err_script
if not exist "%OUTLINE%" goto :err_outline

REM Derive stem + track name + output filename from the JSON.
for %%F in ("%OUTLINE%") do set "FNAME=%%~nF"
set "STEM=!FNAME:_outline=!"
set "TRACKNAME=!STEM:_= !"
set "OUTMP4=%~dp0!STEM!_optimal_lap.mp4"

REM Collect extra CLI args (everything after the JSON path).
if not "%~1"=="" shift
set "EXTRA="
:collect
if "%~1"=="" goto :resolve_telem
set "EXTRA=!EXTRA! %1"
shift
goto :collect

:resolve_telem
REM Per-track mapping: which telemetry CSV to use, and how to fetch it from
REM FastF1 if it's missing. Telemetry is REQUIRED by the script — it drives
REM both the dot's animation timing and the speed readout.
REM
REM TELEM         = path to the CSV the script will read
REM FETCH_YEAR    = year to query FastF1 for if TELEM is missing
REM FETCH_TRACK   = track name as FastF1 expects
set "TELEM="
set "FETCH_YEAR="
set "FETCH_TRACK="
if /I "!STEM!"=="miami_grand_prix" (
    set "TELEM=%~dp0F1_Pipeline_Assets\exports\fastest_miami.csv"
    set "FETCH_YEAR=2024"
    set "FETCH_TRACK=Miami"
)

if "!TELEM!"=="" goto :err_telem_missing

REM Fetch from FastF1 if the CSV is missing.
if not exist "!TELEM!" (
    if "!FETCH_YEAR!"=="" goto :err_telem_path
    echo.
    echo === Fetching fastest weekend lap from FastF1 ===
    echo   year:   !FETCH_YEAR!
    echo   track:  !FETCH_TRACK!
    echo   out:    !TELEM!
    "%PYTHON%" "%~dp0fetch_fastest_lap.py" --year !FETCH_YEAR! --track "!FETCH_TRACK!" --out "!TELEM!"
    if errorlevel 1 (
        echo FastF1 fetch failed.
        pause
        exit /b 1
    )
)

if not exist "!TELEM!" goto :err_telem_path

echo.
echo === Generating optimal racing line video ===
echo   outline:    %OUTLINE%
echo   track:      !TRACKNAME!
echo   telemetry:  !TELEM!
echo   output:     %OUTMP4%
if not "!EXTRA!"=="" echo   extra args:!EXTRA!
echo.

"%PYTHON%" "%SCRIPT%" --outline "%OUTLINE%" --telemetry-csv "!TELEM!" --track-name "!TRACKNAME!" --out "%OUTMP4%"!EXTRA!
set "RC=%errorlevel%"

echo.
if "%RC%"=="0" (
    echo Done.  ^>^>  %OUTMP4%
) else (
    echo FAILED with exit code %RC%
)
pause
exit /b %RC%

:err_py
echo ERROR: Python not found at:
echo   %PYTHON%
pause
exit /b 1

:err_script
echo ERROR: raceline_video.py not found next to this .bat:
echo   %SCRIPT%
pause
exit /b 1

:err_outline
echo ERROR: outline JSON not found:
echo   %OUTLINE%
pause
exit /b 1

:err_telem_missing
echo ERROR: no telemetry CSV mapped for track stem "!STEM!".
echo Add a line to the per-track table in this .bat, e.g.:
echo   if /I "!STEM!"=="bahrain_grand_prix"  set "TELEM=%%~dp0F1_Pipeline_Assets\exports\VER_telemetry_bahrain.csv"
pause
exit /b 1

:err_telem_path
echo ERROR: telemetry CSV not found at:
echo   !TELEM!
pause
exit /b 1
