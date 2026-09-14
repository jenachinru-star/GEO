@echo off
chcp 65001 >nul
echo ========================================
echo   GEO 智能运营中台 - 后端启动
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/2] 检查Python环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo [2/2] 启动后端服务 (端口 8000)...
echo.
echo 后端API文档: http://localhost:8000/docs
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
