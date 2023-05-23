function Add-Bib-to-Biblist([string]$conference_name) {
    if (-not (Test-Path "data/$conference_name.bib.json")) {
        Write-Host "Converting $conference_name.bib to json"
        python bib2json.py `
        -i "raw_data/$conference_name.bib" `
        -o "data/$conference_name.bib.json"
    }

    Write-Host "Adding $conference_name to bib_list"
    Add-Content -Path "bib_list.txt" -Value "data/$conference_name.bib.json"
}

function Cleanup-Biblist {
    Get-Content "bib_list.txt" | Sort-Object | Select-Object -Unique | Set-Content "bib_list.txt";
}