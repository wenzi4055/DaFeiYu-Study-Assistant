<#
    用 Windows 自带 OCR 引擎识别图片文字（零依赖，中文语言包已在系统里）。

        powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\ocr-file.ps1 图片.png
        dir raw_shots\*.png | % { tools\ocr-file.ps1 $_ }

    实测边界：印刷体（界面文字、截图、扫描件）识别率可用；手写体基本认不出。
    手写笔记请走视觉模型，别在这上面耗时间。
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path,
    [string]$Lang = 'zh-Hans-CN'
)

$full = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath

Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
}

function Await($task, $resultType) {
    $m = $asTask.MakeGenericMethod($resultType)
    $netTask = $m.Invoke($null, @($task))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

$language = New-Object Windows.Globalization.Language $Lang
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) {
    Write-Error "OCR 引擎创建失败，确认语言包：$Lang"
    exit 1
}

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

Write-Output "=== $full ==="
foreach ($line in $result.Lines) { Write-Output $line.Text }
