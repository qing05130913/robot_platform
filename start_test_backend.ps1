# 启动测试专用后端：连接测试库 robot_platform_test，并开启测试模式校验。
# 用法（在项目根目录执行）： .\start_test_backend.ps1
$env:DB_NAME = "robot_platform_test"
$env:TEST_MODE = "1"
Set-Location -Path (Join-Path $PSScriptRoot "backend")
uvicorn main:app --reload
