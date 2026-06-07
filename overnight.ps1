$attempt = 0
$cooldown = 300
$prompt = "Read PROGRESS.md to see where the last session ended. Read GOALS.md to find the next incomplete goal item. Then work through as many goal items as you can, in order, writing working code. After completing each item mark it [x] in GOALS.md. After every goal item or every 15 minutes of work (whichever comes first), append a session update to PROGRESS.md documenting exactly what was built, any decisions made, and any blockers. When you cannot continue due to a token limit or context limit, write a final PROGRESS.md entry summarizing the session and stop cleanly."

while ($true) {
    $attempt++
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "$timestamp : Attempt $attempt starting" | Tee-Object -FilePath overnight.log -Append

    claude --dangerously-skip-permissions -p $prompt 2>&1 | Tee-Object -FilePath overnight.log -Append

    if (Test-Path ".stop") {
        Write-Host "$(Get-Date): .stop file found, exiting." | Tee-Object -FilePath overnight.log -Append
        Remove-Item ".stop"
        exit
    }

    Write-Host "$(Get-Date): Waiting $cooldown seconds before retry..." | Tee-Object -FilePath overnight.log -Append
    Start-Sleep -Seconds $cooldown
}
