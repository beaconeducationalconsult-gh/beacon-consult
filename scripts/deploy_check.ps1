<#
  deploy_check.ps1 — the deploy pre-flight, for a Windows checkout.

  This is a thin wrapper: all the checks live in `scripts/verify_deploy.mjs`,
  which needs nothing but Node (already required by the checkout) and is covered
  by `src/deployCheck.test.js`. Keeping the logic out of PowerShell means the
  same script runs on this machine, on the Unix shells in docs/, and in CI —
  and that the checks are tested rather than retyped.

  Usage, from the repository root:

      .\scripts\deploy_check.ps1                                   # local config + build
      .\scripts\deploy_check.ps1 -Url https://beacon.vercel.app     # the whole pre-flight
      .\scripts\deploy_check.ps1 -Url https://beacon.vercel.app -SkipBuild

  Exit code 0 = every check passed. It deploys nothing.
#>
[CmdletBinding()]
param(
  [string]$Url = '',
  [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 negotiates TLS 1.0 by default; Vercel and Firebase refuse it.
try {
  [Net.ServicePointManager]::SecurityProtocol =
    [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
  Write-Host 'node is not on PATH. Install Node 22+ (https://nodejs.org), open a new terminal, and run this again.' -ForegroundColor Red
  exit 1
}

$cliArgs = @('scripts/verify_deploy.mjs')
if ($Url) { $cliArgs += @('-Url', $Url) }
if ($SkipBuild) { $cliArgs += '-SkipBuild' }

& $node.Source @cliArgs
exit $LASTEXITCODE
