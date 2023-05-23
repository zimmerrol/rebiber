. "./add_conf.ps1"

$raw_data_folder = "raw_data"

if (-Not (Test-Path -Path $raw_data_folder)) {
    Write-Host "Cannot find raw_data folder. Execute this script from inside rebiber/rebiber."
    exit
}

$base_conference_ids = @(
    "nips/neurips{0}"
    "icml/icml{0}"
    "iclr/iclr{0}"
    "iccv/iccv{0}"
    "cvpr/cvpr{0}"
)
# "eccv/eccv{0}"
$start_year = 2020
$end_year = [int]$(get-date -Format yyyy) + 1


foreach ($base_conference_id in $base_conference_ids) {
    
    for ($year = $start_year; $year -le $end_year; $year = $year + 1) {
        $conference_id = [string]::Format($base_conference_id, $year)

        $conference_name = $conference_id.split("/")[-1]
        $conference_name_path = Join-Path -Path $raw_data_folder -ChildPath $conference_name
        $base_url = "https://dblp.org/search/publ/api?q=toc%3Adb/conf/{0}.bht%3A&f={1}&h={2}&format=bibtex"
        $idx = 0

        Write-Host "$conference_name_path.bib"
        # Check if full file already exists; if not, download partial files.
        if (Test-Path "$conference_name_path.bib") {
            $idx = -1
            Write-Host "Skipping $conference_name_path.bib"
        } else {
            while ($true) {
                $start = $idx * 1000
                $end = $start + 1000
                $url = [string]::Format($base_url, $conference_id.replace("/", "%2F"), $start, $end)
                $output_name = [string]::Format("{0}-{1}.bib", $conference_name, $idx + 1)
                $output_path = Join-Path -Path $raw_data_folder -ChildPath $output_name
                Write-Host "Downloading $output_path"
                Invoke-WebRequest $url -OutFile $output_path
                if ((Get-Item $output_path).length -eq 0) {
                    Remove-Item $output_path
                    break
                }
                $idx = $idx + 1
            }
        }

        
        if ($idx -gt 0) {
            # Merge files
            Get-Content "$conference_name_path-*.bib" | Set-Content "$conference_name_path.bib"
            Remove-Item "$conference_name_path-*.bib"
        }
        if ($idx -ne 0) {
            # Add new bib files to  file
            Add-Bib-to-Biblist $conference_name
        }
    }
}

Cleanup-Biblist