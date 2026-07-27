@echo off
setlocal enabledelayedexpansion

REM ==== CONFIGURATION ====
set CONTAINER_NAME=valhalla
set IMAGE=ghcr.io/valhalla/valhalla@sha256:83ca136a5c3380182539b5356fb0f779df2ae332641a5ee03a60a826b128a680
set HOST_PORT=8002
set PBF_FILE=bangalore_full.osm.pbf

REM ==== CLEANUP IF ALREADY RUNNING ====
docker rm -f %CONTAINER_NAME% >nul 2>&1

REM ==== START VALHALLA CONTAINER ====
echo Starting Valhalla container...
docker run -dt --name %CONTAINER_NAME% ^
 -v "%cd%\custom_data:/custom_data" ^
 -v "%cd%\conf:/data/conf" ^
 -v "%cd%\custom_data\valhalla_tiles:/data/valhalla" ^
 -p %HOST_PORT%:8002 ^
 %IMAGE%

IF %ERRORLEVEL% NEQ 0 (
  echo  ERROR: Failed to create the Valhalla container.
  exit /b 1
)

REM ==== WAIT FOR CONTAINER TO BE FULLY UP ====
echo Waiting for container to be ready...
timeout /t 3 >nul

REM ==== BUILD THE TILES ====
echo Building tiles from %PBF_FILE% ...
docker exec %CONTAINER_NAME% valhalla_build_tiles -c /data/conf/valhalla.json /custom_data/%PBF_FILE%

IF %ERRORLEVEL% NEQ 0 (
  echo  ERROR: Tile building failed.
  exit /b 1
)

REM ==== START THE VALHALLA SERVICE ====
echo Starting Valhalla service on port %HOST_PORT% ...
docker exec -d %CONTAINER_NAME% valhalla_service /data/conf/valhalla.json

IF %ERRORLEVEL% NEQ 0 (
  echo  ERROR: Failed to start Valhalla service.
  exit /b 1
)

REM ==== DONE ====
echo  Valhalla is now running at http://localhost:%HOST_PORT%
exit /b 0