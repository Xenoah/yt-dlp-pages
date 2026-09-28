@echo off
setlocal
call "%~dp0docs\bridge\start-windows.cmd" %*
exit /b %errorlevel%
