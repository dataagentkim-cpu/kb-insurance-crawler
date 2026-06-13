# 회사에서 이어서 수집하기 (HANDOFF)

## 핵심 개념
- **코드는 GitHub에 있음** → 어느 PC든 `git pull` 로 최신 상태 받기.
- **엑셀 결과물은 실행한 PC에만 생김** (`.gitignore` 에 `*.xlsx` → 깃에 안 올라감).
  따라서 **회사에서 실행하면 파일도 회사 PC에 저장**된다.
- KB 서버(`ppa.kbinsure.co.kr`)는 **사내망/로컬에서만 접속** 가능.
  GitHub Actions(클라우드)는 접속 불가(타임아웃)로 확인됨 → **반드시 로컬 실행**.

## 회사 PC에서 할 일

### 1) 코드 최신화
이미 클론돼 있으면(예: `/Users/hanwha/kb-insurance-crawler`):
```bash
cd ~/kb-insurance-crawler   # 기존 클론 위치
git pull
```
처음이면:
```bash
git clone https://github.com/dataagentkim-cpu/kb-insurance-crawler.git
cd kb-insurance-crawler
```

### 2) 패키지 설치 (최초 1회)
```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

### 3) 수집 실행
**전체 6개 상품** (절전 방지 포함):
- macOS:
  ```bash
  caffeinate -i python3 kb_collect.py
  ```
- Windows (PowerShell):
  ```powershell
  python kb_collect.py        # 스크립트가 실행 중 자동으로 절전 방지
  ```

**상품 하나씩** 돌리고 싶으면:
```bash
python3 kb_collect.py --products 24995          # 한 상품
python3 kb_collect.py --products 24953 24954    # 여러 상품
python3 kb_collect.py --products 24995 --ages 45  # 특정 나이만(테스트용)
```

### 4) 결과 파일 위치
실행한 폴더 안에 생성:
- 상품별: `kb_보험료_<날짜>_<상품코드>_partial.xlsx`
- 통합본: `kb_보험료_<날짜>.xlsx` (모든 상품 한 파일)

## 상품 구성 (현재 6종, 모두 지원)
| 코드 | 상품 | 비고 |
|------|------|------|
| 24953 | 연만기갱신형(표준) | 간편/일반심사, LE+LB |
| 24954 | 연만기갱신형(해약환급금미지급형) | |
| 24957 | 세만기(표준) | 90/95/100세 |
| 24958 | 세만기(해약환급금미지급형) | |
| 24995 | 연만기갱신형(맞춤고지) | LB, 10/20/30년 갱신, batch=1 |
| 24999 | 세만기(맞춤고지) | LA, 90·100세, batch=1 |

## 안정성 (장시간 실행 대비, 이미 코드에 반영)
- 모든 API 호출 45초 hard timeout → 무한 멈춤 차단
- 5000콜마다 page 재생성 + 실패 시 브라우저 자동 재시작
- 조건 처리 하드 실패는 해당 조건만 스킵하고 계속
- 실행 동안 시스템 절전/슬립 방지 (Windows 자동 / macOS 는 `caffeinate -i`)

## 참고
- 24995 는 만 70세 미가입(나이 20~65만 산출됨) — 정상.
- 맞춤고지(24995/24999) 조사·해결 경위는 `INVESTIGATION_24995.md` 참고.
- 집 PC에서 부분 수집된 xlsx 는 그 PC에만 있고 깃엔 없음 — 회사에서 새로 돌리면 됨.
