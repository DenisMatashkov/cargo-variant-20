@echo off
setlocal
pushd "%~dp0" || exit /b 1
py -3 -B -m src.main %*
set "run_exit=%errorlevel%"
popd
exit /b %run_exit%
