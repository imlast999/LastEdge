@echo off
chcp 65001 >nul
call "%~dp0clone_repos.bat" %*
