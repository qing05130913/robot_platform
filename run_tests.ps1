# 运行自动化测试：让 pytest 连接测试库 robot_platform_test。
# 用法（在项目根目录执行）：
#   .\run_tests.ps1                        # 全量
#   .\run_tests.ps1 tests/test_device.py -v   # 单个文件
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)
$env:DB_NAME = "robot_platform_test"
python -m pytest @PytestArgs
