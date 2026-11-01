# 重新打包单文件 exe（Windows）。产物：dist\DaFeiYu.exe
# 用法：右键“使用 PowerShell 运行”，或在终端执行 .\build.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m pip install --quiet --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name DaFeiYu dafeiyu.py

$exe = Join-Path $PSScriptRoot "dist\DaFeiYu.exe"
if (Test-Path $exe) {
    $mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "打包完成：dist\DaFeiYu.exe（$mb MB）"
    Write-Host "分发时把 exe 单独拿走即可；首次运行会在 exe 旁边自动生成 tasks.json 和 dafeiyu_state.json。"
} else {
    Write-Error "打包失败，检查上方的 PyInstaller 输出。"
}
