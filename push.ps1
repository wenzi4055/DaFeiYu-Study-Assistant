# 推送到 GitHub。用法：
#   .\push.ps1
# 推送时 Git Credential Manager 会弹浏览器，点授权即可，不需要手打密码或 token。

param(
    [string]$User = "wenzi4055",
    [string]$Repo = "DaFeiYu-Study-Assistant"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not $User) {
    Write-Host "GitHub 用户名 = github.com/ 后面那一段，不是邮箱。" -ForegroundColor Cyan
    $User = Read-Host "输入你的 GitHub 用户名"
}
$User = $User.Trim().TrimEnd("/")
if (-not $User) { Write-Error "用户名不能为空"; exit 1 }
if ($User -match "@") {
    Write-Error "这是邮箱。请填 github.com/ 后面的用户名，例如 github.com/octocat 里就是 octocat。"
    exit 1
}

$branch = (git branch --show-current).Trim()
$author = (git log -1 --format='%an <%ae>')
Write-Host ""
Write-Host "分支   : $branch"
Write-Host "作者   : $author"
Write-Host "提交数 : $((git rev-list --count HEAD))"

$url = "https://github.com/$User/$Repo.git"
git remote remove origin 2>$null | Out-Null
git remote add origin $url
Write-Host "远程   : $url"
Write-Host ""
Write-Host "开始推送。浏览器弹窗时点 Authorize 授权。" -ForegroundColor Cyan
git push -u origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "推送完成: $url" -ForegroundColor Green
    Write-Host "打开 https://github.com/$User/$Repo 检查 README 和截图是否正常显示。"
} else {
    Write-Host ""
    Write-Host "推送失败。按顺序排查：" -ForegroundColor Yellow
    Write-Host "  1. 仓库是否已在 GitHub 上创建（名字必须是 $Repo，不要勾选 Add README）"
    Write-Host "  2. 用户名是否写错：$User"
    Write-Host "  3. 浏览器授权窗口是不是被关掉了，重跑一次本脚本"
}
