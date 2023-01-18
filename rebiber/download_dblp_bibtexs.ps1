
$base_conference_ids = @(
    "nips/neurips{0}"
    "icml/icml{0}"
    "iclr/iclr{0}"
    "eccv/eccv{0}"
    "iccv/iccv{0}"
    "cvpr/cvpr{0}"
)
$start_year = 2020

foreach ($base_conference_id in $base_conference_ids) {
    #$base_conference_id="nips/neurips{0}"
    
    $year = $start_year
    while ($true) {
        $conference_id = [string]::Format($base_conference_id, $year)

        $conference_name = $conference_id.split("/")[-1]
        $base_url = "https://dblp.org/search/publ/api?q=toc%3Adb/conf/{0}.bht%3A&f={1}&h={2}&format=bibtex"
        $idx = 0
        while ($true) {
            $start = $idx * 1000
            $end = $start + 1000
            $url = [string]::Format($base_url, $conference_id, $start, $end)
            $output = [string]::Format("{0}-{1}.bib", $conference_name, $idx + 1)
            Write-Host $url $output
            Invoke-WebRequest $url -OutFile $output
            if ((Get-Item $output).length -eq 0) {
                Remove-Item $output
                break
            }
            $idx = $idx + 1
        }

        if ($idx -eq 0) {
            break
        }

        # Merge files
        Get-Content "$conference_name-*.bib" | Set-Content "$conference_name.bib"
        Remove-Item "$conference_name-*.bib"

        $year = $year + 1
    }
}
#https://dblp.org/search/publ/api?q=toc%3Adb/conf/nips/neurips2021.bht%3A&f=0&h=1000&format=bibtex
#https://dblp.org/search/publ/api?q=toc%3Adb/conf/nips/neurips2021.bht%3A&f=1000&h=1000&format=bibtex
#https://dblp.org/search/publ/api?q=toc%3Adb/conf/nips/neurips2021.bht%3A&f=0&h=1000&format=bibtex