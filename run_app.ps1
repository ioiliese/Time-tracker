# Script de pornire pentru Time Tracker App

# Ne asiguram ca scriptul ruleaza mereu din folderul in care este salvat
Set-Location -Path $PSScriptRoot

# Functie pentru a gasi executabilul Python pe sistem
function Get-PythonPath {
    # Cautam python in PATH, dar ignoram alias-ul (stub-ul) din WindowsApps care deschide Microsoft Store
    $cmds = Get-Command "python" -All -ErrorAction SilentlyContinue
    foreach ($cmd in $cmds) {
        if ($cmd.Source -and $cmd.Source -notmatch "WindowsApps") {
            return $cmd.Source
        }
    }

    $paths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:PROGRAMFILES\Python312\python.exe",
        "$env:PROGRAMFILES\Python311\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$pythonExe = Get-PythonPath

# Verific daca mediul virtual exista
if (Test-Path ".\.venv\Scripts\activate") {
    Write-Host "Activez mediul virtual..."
    & ".\.venv\Scripts\activate"

} else {
    Write-Host "Mediul virtual nu exista. Fac setup..."

    # Creez folder downloads daca nu exista
    if (!(Test-Path "downloads")) {
        mkdir downloads
    }

    # Descarca Python daca nu exista
    if (!(Test-Path ".\downloads\python-3.12.4-amd64.exe")) {
        Write-Host "Descarca Python 3.12.4..."
        Invoke-WebRequest "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe" -OutFile ".\downloads\python-3.12.4-amd64.exe"
    }

    # Instaleaza Python doar daca nu l-am gasit nicaieri
    if (-not $pythonExe) {
        Write-Host "Instalez Python 3.12.4 (poate dura 1-2 minute)..."
        Start-Process -FilePath ".\downloads\python-3.12.4-amd64.exe" -Wait
        
        Write-Host "Astept sa finalizezi instalarea..."
        $timeout = 300
        while (-not $pythonExe -and $timeout -gt 0) {
            Start-Sleep -Seconds 2
            $pythonExe = Get-PythonPath
            $timeout--
        }
        
        if (-not $pythonExe) {
            Write-Host "Eroare: Nu am putut gasi Python dupa instalare."
            exit
        }
    }

    # Creez alias si mediu virtual
    Write-Host "Creez mediu virtual folosind $pythonExe..."
    Set-Alias local_python $pythonExe
    local_python -m venv .venv

    # Activez mediul virtual
    Write-Host "Activez mediul virtual..."
    & ".\.venv\Scripts\activate"
}

Write-Host "Pornesc aplicatia Time Tracker in fundal..."
Start-Process -FilePath ".\.venv\Scripts\pythonw.exe" -ArgumentList ".\src\main.py"
