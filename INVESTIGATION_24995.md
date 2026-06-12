# 24995 보험료 수집 조사 결과

## 목표
KB 5.10.10 플러스 건강보험 (pdcd: 24995=연만기갱신형, 24999=세만기)를 kb_collect.py에 추가

## 기존 작동 상품
- 24953/24954/24957/24958 → LTI0103805 배치 계산 정상 작동

## 24995 핵심 파라미터 차이

| 항목 | 24953 (작동) | 24995 (문제) |
|------|-------------|-------------|
| comprDesignCfcd | "01" | "05" (맞춤고지방식) |
| smplComprPrdtCfcd | "10" | null/"" |
| LTI0103805 결과 | 보험료 정상 | achngCvrPrem=null |

## 조사한 API들

### LTI0103805 (배치 보험료 계산)
- 24953: comprDesignCfcd="01" → 정상 (LB0001=270원 등)
- 24995: comprDesignCfcd="05" → achngCvrPrem=null 반환
- **원인 불명** — 서버가 comprDesignCfcd="05"를 지원 안 하는 것으로 추정

### LTI0103804 (단일 담보 실시간 계산)
- 24995 LB 담보: achngCvrPrem="0" 반환
- rtimePremCalYn: null (LTI0100403 초기값), saveIntroInfo 후 값 변화 미확인

### LTI0104701 (유사 상품 설계 비교)
- sumPrem=0, 담보 데이터 없음
- stndApcno + pdcd="24995" + cvrComprYn="Y" 조합으로 호출해도 동일

### getApcComprDesignPremCalc (APP_CT 경로, devon=false)
- sumPrem=0, cvrCount=0
- apcno에 담보 정보가 없어서인 것으로 추정

## UI 마법사 흐름 분석

CT01_0495M: Step 1 (피보험자/조건) → Step 2 (담보 선택) → Step 3 (보험료 확인)

### saveIntroInfo() 결과
- apcno 생성 성공 (예: RQ2638844719)
- _currentNaviIndex: 1 (Step 2로 이동)
- **페이지 네비게이션 발생** — 새 프레임을 잡아야 함

### Step 2 문제
- `ds_ltApcCvrInfoDTO`: 456개 담보 (ds.setCellData로 cvrNtrCkYn='1' 설정 가능)
- `fds_ltApcCvrInfoDTO`: 395개 담보 (필터된 뷰)
- **핵심 버그**: ds에서 setCellData로 설정한 값이 fds에 반영 안 됨
  - ds에서 5개 담보 선택 → dsChecked=5, fdsChecked=0
- calRtimeCvrPrem은 fds를 하드코딩으로 참조 → fds가 업데이트 안 되면 API 호출 없음

### procSave() 호출 시 오류
- LTI0100101 호출 → errCode=0 but msg="저장이 완료되지 않았습니다"
- saveApcInfo()가 LTI0100101을 먼저 호출함

## 미해결 문제

1. **fds에 ds 변경사항 반영 안 됨** — WebSquare FilterDataset 동작 방식 이해 필요
   - fds에서 직접 setCellData 가능한지 미확인
   - 이벤트 트리거로 fds 갱신 가능한지 미확인

2. **LTI0103805 comprDesignCfcd="05" 불지원** — 해결책 필요
   - 옵션 A: comprDesignCfcd="01"로 강제 변경해서 테스트
   - 옵션 B: Step 3 화면까지 완전 자동화해서 어떤 API가 호출되는지 캡처
   - 옵션 C: 다른 API 경로 탐색 (아직 미발견)

3. **LTI0100101 저장 실패** — UW 심사 관련 문제
   - "청약안내_문제해결" 클릭 필요 → UI 자동화로 해결 가능할 수 있음

## 다음 시도할 것

### 옵션 A (가장 빠름): comprDesignCfcd 강제 "01"
```python
# kb_collect.py에서 24995에 대해 comprDesignCfcd="01"로 테스트
# 보험료 값이 나오면 실제 "05" 보험료와 동일한지 확인
```

### 옵션 B: fds에서 직접 setCellData 시도
```javascript
// Step 2에서 fds에 직접 설정
const fds = window[prefix + '_fds_ltApcCvrInfoDTO'];
fds.setCellData(0, 'cvrNtrCkYn', '1');  // 가능한지 미확인
fds.setCellData(0, 'achngCvrTnthwnUnitNtramt', '1000');
// → calRtimeCvrPrem이 호출되면 API 요청 캡처
```

### 옵션 C: Step 3까지 완전 자동화
- procSave() 내 LTI0100101 저장 완료 후 naviIndex=2(Step3)로 이동
- Step 3에서 어떤 보험료 조회 API가 호출되는지 확인

## 코드 위치
- `/Users/hanwha/kb-insurance-crawler/kb_collect.py` — 메인 수집기
- `/Users/hanwha/kb-insurance-crawler/probe_24995v*.py` — 조사 스크립트들

## CT01_0495M API 엔드포인트
```
GET https://ppa.kbinsure.co.kr/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1={pdcd}
POST https://ppa.kbinsure.co.kr/po-21/APP_EG/SG_EG/WS/v1/APP_KI/DEVON/{fn}?envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON
```
