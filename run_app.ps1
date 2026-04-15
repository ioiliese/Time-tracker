# Script de pornire pentru Time Tracker App

# Verific daca mediul virtual exista
if (Test-Path ".\.venv\Scripts\activate") {
    Write-Host "Activez mediul virtual..."
    & ".\.venv\Scripts\activate"

    Set-Alias local_python .\python\python.exe
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

    # Instaleaza Python daca nu exista
    if (!(Test-Path ".\python\python.exe")) {
        Write-Host "Instalez Python 3.12.4..."
        .\downloads\python-3.12.4-amd64.exe InstallAllUsers=0 TargetDir="$PWD\python" PrependPath=0
    }

    # Creez alias si mediu virtual
    Write-Host "Creez mediu virtual..."
    Set-Alias local_python .\python\python.exe
    local_python -m venv .venv

    # Activez mediul virtual
    Write-Host "Activez mediul virtual..."
    & ".\.venv\Scripts\activate"
}

Write-Host "Pornesc aplicatia Time Tracker..."
local_python .\src\main.py