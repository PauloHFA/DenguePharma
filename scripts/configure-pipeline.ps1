param([string]$EnvFile = (Join-Path $PSScriptRoot '../.env'))
$ErrorActionPreference = 'Stop'
$pipelineEnvPath = [System.IO.Path]::GetFullPath($EnvFile)
if (-not (Test-Path -LiteralPath $pipelineEnvPath)) {
    throw 'Crie o .env a partir de .env.example e configure as credenciais locais antes de habilitar o pipeline.'
}
$pipelineEnvText = [System.IO.File]::ReadAllText($pipelineEnvPath)
$pipelineMatch = [regex]::Match($pipelineEnvText, '(?m)^PIPELINE_TOKEN=(.*)$')
if ($pipelineMatch.Success -and $pipelineMatch.Groups[1].Value.Trim().Length -ge 32) {
    Write-Host 'O .env ja possui PIPELINE_TOKEN configurado; segredo preservado.'
    exit 0
}
if ($pipelineMatch.Success -and $pipelineMatch.Groups[1].Value.Trim().Length -gt 0) {
    throw 'PIPELINE_TOKEN existente tem menos de 32 caracteres. Ajuste esse valor explicitamente; o script nao substitui segredos existentes.'
}
$pipelineBytes = New-Object byte[] 32
$pipelineRng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $pipelineRng.GetBytes($pipelineBytes) } finally { $pipelineRng.Dispose() }
$pipelineSecret = [Convert]::ToBase64String($pipelineBytes)
if ($pipelineMatch.Success) {
    $pipelineEnvText = $pipelineEnvText.Replace($pipelineMatch.Value, ('PIPELINE_TOKEN=' + $pipelineSecret))
} else {
    $pipelineEnvText = $pipelineEnvText.TrimEnd() + "`r`nPIPELINE_TOKEN=" + $pipelineSecret + "`r`n"
}
[System.IO.File]::WriteAllText($pipelineEnvPath, $pipelineEnvText, [System.Text.UTF8Encoding]::new($false))
Write-Host 'Credencial interna criada no .env sem exibir o segredo. Recarregue o ambiente e reinicie o backend antes de iniciar o worker.'
