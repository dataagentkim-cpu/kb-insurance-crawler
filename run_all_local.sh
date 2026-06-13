#!/bin/bash
# 6개 상품 전량 로컬 수집. 각 프로세스가 SetThreadExecutionState 로 절전 방지.
# KB 서버는 사내망 전용이라 클라우드(Actions) 접속 불가 → 로컬 실행 필수.
cd /c/Users/PC/projects/kb-insurance-crawler
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
echo "=== ALL START $(date +%m-%d_%H:%M) ==="
for P in 24995 24999 24953 24954 24957 24958; do
  echo "=== START $P $(date +%m-%d_%H:%M) ==="
  python kb_collect.py --products "$P" > "run_${P}.log" 2>&1
  echo "=== END $P rc=$? $(date +%m-%d_%H:%M) ==="
done
echo "=== ALL DONE $(date +%m-%d_%H:%M) ==="
