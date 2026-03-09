@echo off

cd /d "%~dp0"

powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/k mytracert.exe'"