# Download public-domain Rider-Waite-Smith tarot 78 cards (data.totl.net, 350x600)
$ErrorActionPreference = 'Stop'
$dest = Join-Path (Split-Path $PSScriptRoot -Parent) 'static\image\rws'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$base = 'http://data.totl.net/tarot-rwcs-images/'
$files = @()
for ($i = 0; $i -le 21; $i++) { $files += ('m{0:d2}.jpg' -f $i) }
foreach ($suit in @('c', 'p', 's', 'w')) {
    for ($i = 1; $i -le 14; $i++) { $files += ('{0}{1:d2}.jpg' -f $suit, $i) }
}
Write-Output "to download: $($files.Count)"
$ok = 0; $fail = @()
foreach ($f in $files) {
    $out = Join-Path $dest $f
    if (Test-Path $out) { $ok++; continue }
    try {
        Invoke-WebRequest -Uri ($base + $f) -OutFile $out -UseBasicParsing -TimeoutSec 40
        $ok++
    } catch {
        $fail += $f
        Write-Output "FAILED: $f -> $($_.Exception.Message)"
    }
    Start-Sleep -Milliseconds 120
}
Write-Output "ok: $ok / $($files.Count)"
if ($fail.Count) { Write-Output "failed list: $($fail -join ', ')" }
$total = (Get-ChildItem $dest -Filter '*.jpg' | Measure-Object Length -Sum).Sum
Write-Output ("total size: {0:N2} MB" -f ($total / 1MB))
