@echo off
chcp 65001 >nul
echo ========================================
echo   GEO 智能运营中台 - 前端启动
echo ========================================
echo.

cd /d "%~dp0frontend"

echo [1/2] 检查Node.js环境...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Node.js，请先安装Node.js 18+
    pause
    exit /b 1
)

echo [2/2] 启动前端开发服务器 (端口 3000)...
echo.
echo 前端访问地址: http://localhost:3000
echo 按 Ctrl+C 停止服务
echo.

npm run dev

pause
