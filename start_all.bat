@echo off
chcp 65001 >nul
cd /d D:\projects\shuai\ShuaiTravelAgent

echo ============================================
echo   小帅旅游助手 - 一键启动
echo ============================================
echo.

REM 启动 API 服务
echo [1/2] 启动 Web API 服务...
start "ShuaiTravelAgent API" cmd /k "call conda activate agents && cd /d D:\projects\shuai\ShuaiTravelAgent && python run_api.py"

timeout /t 3 /nobreak >nul

REM 启动前端
echo [2/2] 启动前端服务...
start "ShuaiTravelAgent Frontend" cmd /k "cd /d D:\projects\shuai\ShuaiTravelAgent\frontend && npm run dev"

echo.
echo ============================================
echo   服务启动中...
echo ============================================
echo.
echo 前端: http://localhost:33001
echo API:  http://localhost:38000
echo 文档: http://localhost:38000/rapidoc
echo.
echo 关闭所有服务请关闭打开的命令行窗口
echo.
pause
