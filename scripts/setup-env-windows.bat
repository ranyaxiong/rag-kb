@echo off
echo 🔐 设置OpenAI API Key到Windows系统环境变量
echo.

set /p api_key="请输入你的OpenAI API Key: "

if "%api_key%"=="" (
    echo ❌ API Key不能为空
    pause
    exit /b 1
)

echo.
echo 🔧 正在设置系统环境变量...

rem 设置用户级环境变量
setx OPENAI_API_KEY "%api_key%"

if %errorlevel% equ 0 (
    echo ✅ API Key已成功设置到用户环境变量
    echo 📝 变量名: OPENAI_API_KEY
    echo 🔄 请重新打开命令提示符以使环境变量生效
    echo.
    echo 💡 现在你可以运行 ./scripts/start.sh 启动服务
) else (
    echo ❌ 设置环境变量失败
    echo 💡 你也可以手动在系统设置中添加环境变量：
    echo    变量名: OPENAI_API_KEY
    echo    变量值: %api_key%
)

echo.
pause