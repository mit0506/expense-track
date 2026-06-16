$CorrectName = "toxicbishop"
$CorrectEmail = "pranavarun19@gmail.com"

$MailmapContent = @"
$CorrectName <$CorrectEmail> dependabot[bot]
$CorrectName <$CorrectEmail> copilot-swe-agent[bot]
$CorrectName <$CorrectEmail> Copilot
$CorrectName <$CorrectEmail> github-advanced-security[bot]
"@

Set-Content -Path "temp_mailmap.txt" -Value $MailmapContent -Encoding UTF8

$RemoteUrl = git config --get remote.origin.url

# Run git filter-repo
C:\Users\Levono\AppData\Local\Programs\Python\Python312\Scripts\git-filter-repo.exe --mailmap temp_mailmap.txt --force

if ($RemoteUrl) {
    git remote add origin $RemoteUrl
    Write-Host "Restored remote origin: $RemoteUrl"
}

Remove-Item "temp_mailmap.txt"

Write-Host "Bot authors have been replaced successfully."
Write-Host "You can now push the changes with: git push --force --all"
