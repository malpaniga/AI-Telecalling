@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0redeploy.ps1" %*
