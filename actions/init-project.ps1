param(
    [Parameter(Mandatory = $true)]
    [string]$NewName
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Slug = ($NewName.ToLower() -replace '[^a-z0-9]+', '-').Trim('-')

Write-Host "[init-project] app.name -> '$NewName', slug -> '$Slug'"

$configPath = Join-Path $RepoRoot "src\configs\config.yaml"
(Get-Content $configPath) `
    -replace '^  name: .*', "  name: $NewName" `
    -replace 'path: logs/app\.log', "path: logs/$Slug.log" |
    Set-Content -Encoding utf8 $configPath

$envExamplePath = Join-Path $RepoRoot "src\.env.example"
(Get-Content $envExamplePath) `
    -replace '^DB_NAME=.*', "DB_NAME=$Slug" `
    -replace '^POSTGRES_DB=.*', "POSTGRES_DB=$Slug" |
    Set-Content -Encoding utf8 $envExamplePath

$composePath = Join-Path $RepoRoot "docker-compose.yml"
(Get-Content $composePath) -replace 'db_data:', "${Slug}_db_data:" |
    Set-Content -Encoding utf8 $composePath

Write-Host "[init-project] Done. Review the diff (git diff), then:"
Write-Host "  1. Copy src\.env.example to src\.env and fill in real secrets."
Write-Host "  2. Delete this script and actions/init-project.sh once you're happy with the result."
Write-Host "  3. Run the test suite: cd src; python -m pytest"
