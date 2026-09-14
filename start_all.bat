@echo off
chcp 65001 >nul
echo ========================================
echo   GEO 智能运营中台 - 一键启动
echo ========================================
echo.

echo 正在启动后端服务...
start "GEO后端" cmd /k "%~dp0start_backend.bat"

timeout /t 3 /nobreak >nul

echo 正在启动前端服务...
start "GEO前端" cmd /k "%~dp0start_frontend.bat"

echo.
echo ========================================
echo   启动完成！
echo   前端: http://localhost:3000
echo   后端API: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo ========================================
echo.
pause
