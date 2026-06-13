#!/bin/bash
# 남은 상품을 각각 독립 프로세스(새 브라우저)로 수집.
# 코드 자체에 evaluate 타임아웃·재시작·page 재생성 내장 → hang 시 자가복구.
cd /c/Users/PC/projects/kb-insurance-crawler
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
for P in 24995 24999 24957 24958; do
  echo "=== START $P $(date +%m-%d_%H:%M) ==="
  python kb_collect.py --products "$P" > "run_${P}.log" 2>&1
  echo "=== END $P rc=$? $(date +%m-%d_%H:%M) ==="
done
echo "=== ALL DONE $(date +%m-%d_%H:%M) ==="
