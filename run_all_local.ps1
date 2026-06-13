# 6개 상품 전량 로컬 수집 (절전방지는 kb_collect.py 내부 처리).
# 독립 프로세스로 Start-Process 실행 → 세션 종료와 무관하게 끝까지 동작.
Set-Location "C:\Users\PC\projects\kb-insurance-crawler"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
"=== ALL START $(Get-Date -Format 'MM-dd_HH:mm') ===" | Out-File -Encoding utf8 run_all.log
foreach ($p in @("24995","24999","24953","24954","24957","24958")) {
  "=== START $p $(Get-Date -Format 'MM-dd_HH:mm') ===" | Out-File -Append -Encoding utf8 run_all.log
  python kb_collect.py --products $p *> "run_$p.log"
  "=== END $p rc=$LASTEXITCODE $(Get-Date -Format 'MM-dd_HH:mm') ===" | Out-File -Append -Encoding utf8 run_all.log
}
"=== ALL DONE $(Get-Date -Format 'MM-dd_HH:mm') ===" | Out-File -Append -Encoding utf8 run_all.log
