$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3 is required for the independent reference check."
}
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    throw "Rust/Cargo is required. Install the toolchain declared in rust-toolchain.toml."
}

python reference/verify_algorithm1.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $env:RAYON_NUM_THREADS) {
    $env:RAYON_NUM_THREADS = "8"
}
Write-Output "RUN_ENV,RAYON_NUM_THREADS=$env:RAYON_NUM_THREADS"

if ($args.Count -eq 0) {
    $arguments = @("--samples", "3")
} else {
    $arguments = $args
}

cargo run --release --locked -- @arguments
exit $LASTEXITCODE
