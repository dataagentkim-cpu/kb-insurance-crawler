"""
KB손해보험 보험료 수집기

실행:
  python3 kb_collect.py
  python3 kb_collect.py --products 24953 24954
  python3 kb_collect.py --ages 30 40 50

결과: kb_보험료_YYYYMMDD.xlsx
"""
import asyncio, json, argparse, re
from datetime import date
from itertools import product as iproduct
from pathlib import Path
import pandas as pd
from playwright.async_api import async_playwright

TODAY      = date.today().strftime("%Y-%m-%d")
TODAY_NUM  = date.today().strftime("%Y%m%d")
ROOT       = Path(__file__).parent
API_QUERY  = "envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON"
API_ORIGIN = "https://ppa.kbinsure.co.kr"

PRODUCTS = {
    "24953": "연만기갱신형(표준)",
    "24954": "연만기갱신형(해약환급금미지급형)",
    "24957": "세만기(표준)",
    "24958": "세만기(해약환급금미지급형)",
}

# 심사고지유형: ltiordCd
SIMSA = [
    ("14", "간편심사(3.0.5)"),
    ("03", "간편심사(3.3.5)"),
    ("00", "일반심사"),
]

# 납입면제: ltigenCd
NAPIM = [
    ("04", "5대납입면제기본형"),
    ("00", "납입면제미적용형"),
]

# 플랜: lngtrmContTdcd
PLAN = [
    ("01", "간편심사형"),
    ("11", "암동시가입"),
    ("02", "일반심사형"),
]

# 심사고지유형 → 허용 플랜 (lngtrmContCndtnCnfrtDTO 분석 결과)
SIMSA_PLAN_ALLOW = {
    "14": {"01", "11"},   # 간편심사(3.0.5)
    "15": {"01", "11"},
    "16": {"01", "11"},
    "03": {"01", "11"},
    "17": {"01", "11"},
    "04": {"01", "11"},
    "00": {"02"},          # 일반심사 → 일반심사형만
}

# 납입면제 → 허용 플랜
NAPIM_PLAN_ALLOW = {
    "04": {"01", "02", "11"},
    "00": {"01", "02", "04", "11"},
}

# 납기/만기 조합 (연만기갱신형용)
# ltifmCd, pymnPrdYrcntCd, insMtrtyYrcntCd, label
PERIODS_YEON = [
    ("01", "10", "10", "10년납/10년만기"),
    ("02", "15", "15", "15년납/15년만기"),
    ("03", "20", "20", "20년납/20년만기"),
    ("04", "30", "30", "30년납/30년만기"),
]

# 세만기 납기/만기 (제품 조건 확인 필요 - 임시값)
PERIODS_SE = [
    ("01", "10", "10", "10년납/10년만기"),
    ("02", "15", "15", "15년납/15년만기"),
    ("03", "20", "20", "20년납/20년만기"),
    ("04", "30", "30", "30년납/30년만기"),
]

# 성별
SEXES = [("1", "남"), ("2", "여")]

# 직업 코드 (ocptCd, ocptCdNm, rateGrade, riskGrdCd, jobgrpGrade)
OCCUPATIONS = [
    ("B014", "전업주부",   "1", "A", "04"),
    # 아래는 LTI0100803으로 조회 후 추가
    # ("B001", "사무원",   "1", "A", "04"),
]

# 운전형태
DRIVS = [("01", "자가용"), ("03", "비운전자형")]

# 기본 담보 가입금액 (만원 단위)
DEFAULT_CVR_AMT_MAN = 1000   # 1,000만원 기준 (단위: 만원)

# ── 세션 관련 전역 상태 ──────────────────────────────────
_prohead_tpl: dict = {}
_syshead_tpl: dict = {}
_treat_org:  dict = {}   # ltApcTreatOrgDTO (직원/지점 정보)
_page = None  # Playwright page


def _make_req_json(fn_name: str, body: dict) -> str:
    """PROHEAD/SYSHEAD를 포함한 요청 JSON 생성"""
    ph = dict(_prohead_tpl)
    ph["pfmFnName"] = fn_name
    ph["pfmGlobalNo"] = ""
    ph["pfmTrDate"]   = ""
    ph["pfmTrTime"]   = ""
    return json.dumps({"PROHEAD": ph, "SYSHEAD": dict(_syshead_tpl), **body},
                      ensure_ascii=False)


async def _call_api(fn_name: str, body: dict) -> dict:
    """page.evaluate 를 통해 fetch() 호출 - 세션 쿠키 자동 포함"""
    url = f"{API_ORIGIN}/po-21/APP_EG/SG_EG/WS/v1/APP_KI/DEVON/{fn_name}?{API_QUERY}"
    req_json = _make_req_json(fn_name, body)
    script = f"""
    async () => {{
        const resp = await fetch({json.dumps(url)}, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: {json.dumps(req_json)},
        }});
        const text = await resp.text();
        try {{ return JSON.parse(text); }} catch(e) {{ return {{_raw: text}}; }}
    }}
    """
    result = await _page.evaluate(script)
    return result or {}


async def init_session():
    """Playwright 브라우저 열기 + PROHEAD/SYSHEAD/TreatOrg 캡처"""
    global _prohead_tpl, _syshead_tpl, _treat_org, _page

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    _page = await browser.new_page()

    captured = {}

    async def on_response(resp):
        try:
            if "LTI0102102" in resp.url and "PROHEAD" not in captured:
                body = await resp.json()
                ph = body.get("PROHEAD", {})
                sh = body.get("SYSHEAD", {})
                if ph:
                    captured["PROHEAD"] = ph
                    captured["SYSHEAD"] = sh
            elif "getUpOrgInfoByEmpNo" in resp.url and "ORG" not in captured:
                body = await resp.json()
                org = body.get("EmpOrgDTO", {})
                if org:
                    captured["ORG"] = org
        except Exception:
            pass

    _page.on("response", on_response)

    url = f"{API_ORIGIN}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1=24953"
    print("▶ 세션 초기화 (브라우저 로딩)...")
    await _page.goto(url)
    await _page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)

    if not captured.get("PROHEAD"):
        raise RuntimeError("세션 초기화 실패: PROHEAD/SYSHEAD를 캡처하지 못했습니다.")

    _prohead_tpl = captured["PROHEAD"]
    _prohead_tpl["pfmFnCd"] = "CT01_0495M"
    _syshead_tpl = captured["SYSHEAD"]

    # ltApcTreatOrgDTO 구성 (직원/지점 정보)
    emp_no = _syshead_tpl.get("pfmEmpNo", "")
    org = captured.get("ORG", {})
    _treat_org = {
        "usCd":           None,
        "usNm":           None,
        "mngtEmpCd":      emp_no,
        "mngtEmpNm":      org.get("empNm") or org.get("mngtEmpNm", ""),
        "mngtOfcd":       None,
        "mngtOfficeNm":   None,
        "mngtBrccd":      org.get("brccd") or org.get("mngtBrccd", ""),
        "mngtBrchofNm":   org.get("brchofNm") or org.get("mngtBrchofNm", ""),
        "ctcd":           org.get("ctcd", ""),
        "cntrNm":         org.get("cntrNm", ""),
        "hqCd":           org.get("hqCd") or org.get("ctcd", ""),
        "slctnOrgGrdCd":  "02",
        "upOrgChngYn":    None,
        "usInputObjcYn":  None,
        "indcEmpNo":      None,
        "indcNm":         None,
    }
    print(f"  ✓ 세션 확보 (userId={_prohead_tpl.get('pfmUserId')}, empNo={emp_no})")
    return browser


async def get_coverage_list(pdcd: str) -> list[dict]:
    """LTI0100403: 담보 목록 조회"""
    body = {
        "LngtrmNtrpsblCvrInqCndtnInfoDTO": {
            "pdcd": pdcd,
            "stdt": TODAY,
            "objctTpcd": "L00001",
        }
    }
    resp = await _call_api("LTI0100403", body)
    items = resp.get("LngtrmApcCvrInfoPDTO", {}).get("ltApcCvrInfoDTO", [])
    print(f"  담보 목록({pdcd}): {len(items)}개")
    return items


async def get_ocpt_grade(ocpt_cd: str) -> dict:
    """LTI0100803: 직업 위험등급 조회"""
    body = {
        "LngtrmOcptInfoDTO": {
            "ocptCd": ocpt_cd,
            "stdt": TODAY,
            "olcdYn": "N",
        }
    }
    resp = await _call_api("LTI0100803", body)
    return resp.get("LngtrmOcptInfoDTO", {})


_NULL_CVR = {"objctSeq": None, "objctTpcd": None, "cvrCd": None, "cvrNm": None, "cvrNtrSeq": None, "cvrTpcd": None, "mobilCvrTpcd": None, "cvrNtrCkYn": None, "ntramtInputYn": None, "pymnPrdInputYn": None, "insPrdInputYn": None, "cvrDtlInputYn": None, "usePcscrId": None, "cvrSuplmtButtonRvtztYn": None, "achngCvrPerpsNtramt": None, "achngCvrPeraccNtramt": None, "achngCvrTnthwnUnitNtramt": None, "cvrAchngCvrNtramt": None, "cvrAchngInsMtrtyYrcnt": None, "cvrAchngInsMtrtyYrcntCd": None, "cvrAchngInsMtrtyYrcntCdNm": None, "cvrAchngInsMtrtyCfcd": None, "achngInsMtrtyAddtnCd": None, "insMtrtyValue": None, "cvrAchngPymnPrdYrcnt": None, "cvrAchngPymnPrdYrcntCd": None, "cvrAchngPymnPrdYrcntCdNm": None, "cvrAchngPymnPrdCfcd": None, "cvrAchngInsPrdYrcnt": None, "pymnPrdValue": None, "achngPymnPrdAddtnCd": None, "cvrAchngInsBgdt": None, "cvrAchngInsEnddt": None, "cvrScrenDispOrd": None, "lngtrmUdtmnAcumCcd": None, "achngCvrPrem": None, "premCalYn": None, "basicCvrYn": None, "cvrChrctrCd": None, "rtimePremCalYn": None, "rtimePrem": None, "cvrRnwlCyclCd": None, "insBgdtStingCfcd": None, "insBgdtStingClsfcValue": None, "ntrpsblCvrTpcd": None, "achngStrtRsrvAge": None, "strtRsrvAgeInputYn": None, "achngRsrvCvrPrem": None, "guarntClmrsvCalTpcd": None, "cvrFullNm": None, "bestNtrLimitAmt": None, "cvrPremKey": None, "incproRate": None, "stdUnbodyGrdCd": None, "guarntChrctrCd": None, "screnDispTypeCfcd": None, "rldmgStablDcPrem": None, "embrPrvuseCvrYn": None, "deletedYn": None, "embrCvrPrem": None, "screnDispOrd": None, "upCvrCd": None, "fcastCsmAmt": None, "proftMltpl": None, "embrRldmgStablDcPrem": None, "sametmNtrCfcd": None, "cvrDcAfPrem": None, "cvrInsert": None, "dcicpPrem": None, "stdUnbodyRiskEpnt": None}
_NULL_PRPRT_CVR = {"groupSeq": None, "objctSeq": None, "objctTpcd": None, "objctTypeNm": None, "cvrCd": None, "cvrNm": None, "cvrNtrSeq": None, "cvrDtlInputYn": None, "cvrNtrCkYn": None, "ntramtInputYn": None, "usePcscrId": None, "cvrSuplmtButtonRvtztYn": None, "cvrAchngInsBgdt": None, "cvrAchngInsEnddt": None, "cvrAchngInsMtrtyYrcnt": None, "cvrAchngInsMtrtyYrcntCd": None, "cvrAchngInsMtrtyYrcntCdNm": None, "cvrAchngInsMtrtyCfcd": None, "cvrAchngPymnPrdYrcnt": None, "cvrAchngPymnPrdYrcntCd": None, "cvrAchngPymnPrdYrcntCdNm": None, "cvrAchngPymnPrdCfcd": None, "cvrAchngInsPrdYrcnt": None, "cvrAchngCvrNtramt": None, "achngCvrTnthwnUnitNtramt": None, "achngCvrPerpsNtramt": None, "achngCvrPeraccNtramt": None, "achngCvrPrem": None, "cvrScrenDispOrd": None, "cvrFullNm": None, "screnDispTypeCfcd": None, "fcastCsmAmt": None, "proftMltpl": None}
_NULL_RATE_FCTR = {"loctSeq": None, "groupSeq": None, "objctSeq": None, "cvrCd": None, "cvrNtrSeq": None, "pdcrtItmId": None, "nmrItmval": None, "charItmval": None}
_NULL_DISBL = {"apcCncpsSeq": None, "custNo": None, "apcCncpsTpcd": None, "disblCfcd": None, "disblValidBgdt": None, "disblValidEnddt": None, "disblScopeCfcd": None}
_NULL_RVW = {"objctSeq": None, "apcno": None, "udtmnVioltYn": None, "udtmnSeq": None, "hmnRvwApplObjcYn": None, "uwObjcCfcd": None, "apcCncpsSeq": None, "partySeq": None, "lngtrmUdtmnDlngCfcd": None, "lngtrmUdtmnDtxt": None, "lngtrmUdtmnId": None, "manualDtlSeq": None, "manualHelpTpcd": None, "ctccBfMngtObjcYn": None, "lngtrmManualClcd": None, "acumStndCfcd": None, "lngtrmUdrtkCvrPurpCd": None, "acumStndSeq": None, "cmmlSeq": None, "lngtrmUdtmnClcd": None, "acumExcsAmt": None, "acumStamt": None, "objctTypeCvrPurpCd": None, "uwDcdarbCd": None, "orgCd": None, "filtrCltrCdLt": None, "lngtrmUdtmnTtxt": None}
_NULL_AUTO_RVW = {"lngtrmUdtmnClcd": None, "udtmnVioltYn": None, "udtmnSeq": None, "hmnRvwApplObjcYn": None, "cvrCd": None, "cvrNm": None, "cvrNtrSeq": None, "pdcrtItmId": None, "charItmval": None, "prdtManualGroupNo": None, "cmmlSeq": None, "cmmlEcctSeq": None, "pdcrtItmHnglNm": None, "rpsntErrMsgCd": None, "ctCd": None, "apcno": None, "uwDcdarbCd": None, "uwObjcCfcd": None, "apcCncpsSeq": None, "objctSeq": None, "acumExcsAmt": None, "acumStamt": None, "objctTypeCvrPurpCd": None, "orgCd": None, "lngtrmUdtmnDlngCfcd": None, "cvrScrenDispOrd": None, "lngtrmUdtmnDtxt": None, "acumStndCfcd": None, "dlngYn": None, "partySeq": None}


async def create_apcno(pdcd: str, cond: dict) -> str | None:
    """LTI0100106: 청약 생성 → apcno 반환"""
    body = {
        "LtApcBasicInfoDTO": {
            "ltApcComnDTO":                  _make_comnDTO(pdcd, apcno=None, wrcls="I"),
            "ltApcTreatOrgDTO":              dict(_treat_org),
            "ltApcPolhdInfoDTO":             {},
            "ltApcObjDtlDTO":               [_make_objDTO(cond)],
            "ltApcContCndtnDTO":             _make_cndtnDTO(pdcd, cond),
            "ltApcDcRateInfoDTO":           [],
            "ltApcCvrInfoDTO":              [dict(_NULL_CVR)],
            "ltApcPremDTO":                 {"acprm": None, "guarntPrem": 0},
            "ltApcBnfcryDTO":               {},
            "ltApcSettlBkacntDTO":          {},
            "ltApcPyBkacntDTO":             {},
            "ltApcInsdpsSuplmtInfoDTO":     [],
            "ltApcContchngObjcDTO":         [],
            "ltApcLoctInfoDTO":             [],
            "ltApcPrprtGroupInfoDTO":       [],
            "ltApcNtrPrprtCvrDTO":          [dict(_NULL_PRPRT_CVR)],
            "ltApcNtrPrprtEtcCvrDTO":       [dict(_NULL_PRPRT_CVR)],
            "ltApcPrprtRateFctrInfoDTO":    [dict(_NULL_RATE_FCTR)],
            "ltApcCncpsDisblDeductInfoDTO": [dict(_NULL_DISBL)],
            "ltApcbfContInfoDTO":           [],
            "ltApcCmpanmlInfoDTO":          [],
            "etcMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],
            "cvrMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],
            "lngtrmAutoRvwPDTO":            [dict(_NULL_AUTO_RVW)],
        }
    }
    resp = await _call_api("LTI0100106", body)
    err = resp.get("ErrorCode", "")
    if err != "0":
        print(f"  ⚠ LTI0100106 오류 ({err}): {resp.get('ErrorMsg','')}")
        return None
    apcno = resp.get("ltApcBasicInfoOutDTO", {}).get("ltApcComnDTO", {}).get("apcno")
    return apcno


BATCH_SIZE   = 20   # LTI0103805 서버 한 번에 처리 가능한 최대 담보 수
CONCURRENCY  = 10   # 동시 병렬 배치 요청 수


async def _call_prem_batch(apcno: str, pdcd: str, cond: dict, batch: list[dict]) -> dict:
    """LTI0103805 단일 배치 호출, {cvrCd: prem} 반환"""
    body = {
        "LngtrmApcRtimePremInqInfoDTO": {
            "rtimeCalYn": "Y",
            "ltApcComnDTO": _make_comnDTO(pdcd, apcno=apcno, wrcls="D"),
            "ltApcContCndtnDTO": _make_cndtnDTO(pdcd, cond),
            "ltApcObjDtlDTO": _make_objDTO(cond),
            "ltApcCvrPremSuplmtInfoDTO": {},
            "ltApcCvrInfoDTO": batch,
        }
    }
    resp = await _call_api("LTI0103805", body)
    err = resp.get("ErrorCode", "")
    if str(err) != "0":
        return {"_error": resp.get("ErrorMsg", str(err))}
    out = resp.get("LTI0103805_O", {})
    cvr_results = out.get("ltApcCvrInfoDTO", [])
    if not isinstance(cvr_results, list):
        cvr_results = [cvr_results]
    result = {}
    for item in cvr_results:
        cd = item.get("cvrCd", "")
        prem = item.get("achngCvrPrem")
        if cd and prem is not None:
            result[cd] = int(prem)
    return result


async def get_premium(apcno: str, pdcd: str, cond: dict, cvr_list: list[dict]) -> dict:
    """LTI0103805: 담보별 보험료 일괄 조회 (병렬 배치)
    Returns: {cvrCd: prem_원}
    """
    valid_simsa = cond.get("ltiordCd", "14")
    if valid_simsa == "00":
        prefix_ok = lambda cd: cd.startswith("LB")
    else:
        prefix_ok = lambda cd: cd.startswith("LE")

    amt  = DEFAULT_CVR_AMT_MAN * 10000
    unit = DEFAULT_CVR_AMT_MAN

    send_cvrs = []
    for cvr in cvr_list:
        cd = cvr.get("cvrCd", "")
        if not prefix_ok(cd):
            continue
        send_cvrs.append({
            "objctSeq": "1",
            "objctTpcd": cvr.get("objctTpcd", "L00001"),
            "cvrCd": cd,
            "cvrNm": cvr.get("cvrNm", ""),
            "cvrNtrSeq": cvr.get("cvrNtrSeq", "1"),
            "cvrTpcd": cvr.get("cvrTpcd", ""),
            "cvrNtrCkYn": "1",
            "ntramtInputYn": cvr.get("ntramtInputYn", "Y"),
            "pymnPrdInputYn": cvr.get("pymnPrdInputYn", "N"),
            "insPrdInputYn": cvr.get("insPrdInputYn", "N"),
            "cvrSuplmtButtonRvtztYn": "N",
            "achngCvrPerpsNtramt": amt,
            "achngCvrTnthwnUnitNtramt": unit,
            "cvrAchngCvrNtramt": amt,
            "cvrFullNm": cvr.get("cvrFullNm", cvr.get("cvrNm", "")),
            "ntrpsblCvrTpcd": cvr.get("ntrpsblCvrTpcd", ""),
            "screnDispOrd": cvr.get("screnDispOrd", "1"),
        })

    if not send_cvrs:
        return {}

    batches = [send_cvrs[i:i + BATCH_SIZE] for i in range(0, len(send_cvrs), BATCH_SIZE)]

    # 세마포어로 동시 요청 수 제한
    sem = asyncio.Semaphore(CONCURRENCY)
    async def bounded(batch):
        async with sem:
            return await _call_prem_batch(apcno, pdcd, cond, batch)

    results = await asyncio.gather(*[bounded(b) for b in batches])

    combined = {}
    for r in results:
        if "_error" in r:
            return r
        combined.update(r)
    return combined


def _make_comnDTO(pdcd: str, apcno, wrcls: str) -> dict:
    return {
        "wrClsfc": wrcls,
        "apcno": apcno,
        "apcDay": TODAY,
        "insBgdt": TODAY,
        "insEnddt": None,
        "apcSttcd": None if wrcls == "I" else "00",
        "apcJobKindCfcd": "01",
        "saleChCfcd": "01",
        "systemChfcd": "23",
        "pdcd": pdcd,
        "prdtClcd": "202",
        "inputScrenCfcd": "21",
        "rncvrSptnApplYn": "Y",
    }


def _make_cndtnDTO(pdcd: str, cond: dict) -> dict:
    prd = cond.get("pymnPrdYrcntCd", "10")
    mty = cond.get("insMtrtyYrcntCd", "10")
    fm  = cond.get("ltifmCd", "01")
    return {
        "ltictCd":          "03",
        "ltifmCd":          fm,
        "lngtrmContTdcd":   cond.get("lngtrmContTdcd", "01"),
        "pymnPrdYrcnt":     None,
        "pymnPrdYrcntCd":   prd,
        "pymnPrdCfcd":      "1",
        "insMtrtyYrcnt":    None,
        "insMtrtyYrcntCd":  mty,
        "insMtrtyCfcd":     "1",
        "insPrdYrcnt":      None,
        "pymnCyclCd":       "L10",
        "smplComprPrdtCfcd": "10",
        "ltigenCd":         cond.get("ltigenCd", "04"),
        "ltifamCd":         None,
        "ltiordCd":         cond.get("ltiordCd", "14"),
        "comprDesignCfcd":  "01",
    }


def _make_objDTO(cond: dict) -> dict:
    return {
        "objctSeq":       "1",
        "objtyCfcd":      "L001",
        "objctTpcd":      "L00001",
        "insdpsCncpsSeq": None,
        "sexCd":          cond["sexCd"],
        "insAge":         str(cond["insAge"]),
        "fulage":         str(cond["insAge"]),
        "ocptCd":         cond["ocptCd"],
        "ocptCdNm":       cond["ocptCdNm"],
        "rateGrade":      cond["rateGrade"],
        "riskGrdCd":      cond["riskGrdCd"],
        "jobgrpGrade":    cond["jobgrpGrade"],
        "insdpsRlcd":     "001",
        "drivTdcd":       cond["drivTdcd"],
        "objtyInsBgdt":   TODAY,
        "embrYn":         "N",
        "objctSttcd":     "01",
        "partyMncnt":     "1",
        "objGuarntPrem":  0,
    }


def build_conditions(pdcd: str, ages: list[int]) -> list[dict]:
    """조건 조합 목록 생성"""
    is_yeon = pdcd in ("24953", "24954")
    periods = PERIODS_YEON if is_yeon else PERIODS_SE

    conds = []
    for (sex_cd, sex_nm) in SEXES:
        for age in ages:
            for (ocpt_cd, ocpt_nm, rg, rc, jg) in OCCUPATIONS:
                for (driv_cd, driv_nm) in DRIVS:
                    for (simsa_cd, simsa_nm) in SIMSA:
                        for (napim_cd, napim_nm) in NAPIM:
                            for (plan_cd, plan_nm) in PLAN:
                                # 유효하지 않은 조합 스킵
                                allowed_plan = (SIMSA_PLAN_ALLOW.get(simsa_cd, set()) &
                                                NAPIM_PLAN_ALLOW.get(napim_cd, set()))
                                if plan_cd not in allowed_plan:
                                    continue
                                for (fm_cd, prd_cd, mty_cd, prd_nm) in periods:
                                    conds.append({
                                        "pdcd":           pdcd,
                                        "sexCd":          sex_cd,
                                        "sex_nm":         sex_nm,
                                        "insAge":         age,
                                        "ocptCd":         ocpt_cd,
                                        "ocptCdNm":       ocpt_nm,
                                        "rateGrade":      rg,
                                        "riskGrdCd":      rc,
                                        "jobgrpGrade":    jg,
                                        "drivTdcd":       driv_cd,
                                        "driv_nm":        driv_nm,
                                        "ltiordCd":       simsa_cd,
                                        "simsa_nm":       simsa_nm,
                                        "ltigenCd":       napim_cd,
                                        "napim_nm":       napim_nm,
                                        "lngtrmContTdcd": plan_cd,
                                        "plan_nm":        plan_nm,
                                        "ltifmCd":        fm_cd,
                                        "pymnPrdYrcntCd": prd_cd,
                                        "insMtrtyYrcntCd": mty_cd,
                                        "period_nm":      prd_nm,
                                    })
    return conds


def save_excel(rows: list[dict], suffix: str = ""):
    if not rows:
        return
    df = pd.DataFrame(rows)
    fname = ROOT / f"kb_보험료_{TODAY_NUM}{suffix}.xlsx"
    df.to_excel(fname, index=False)
    print(f"  ✅ 저장: {fname} ({len(df):,}행)")


async def main(args):
    browser = await init_session()
    all_rows: list[dict] = []

    try:
        target_pdcds = args.products if args.products else list(PRODUCTS.keys())
        ages = args.ages if args.ages else list(range(20, 71, 5))  # 20~70, 5세 간격

        for pdcd in target_pdcds:
            print(f"\n▶ 상품 {pdcd} ({PRODUCTS.get(pdcd,'')})")
            cvr_list = await get_coverage_list(pdcd)
            cvr_names = {c["cvrCd"]: c["cvrNm"] for c in cvr_list}

            conds = build_conditions(pdcd, ages)
            print(f"  조건 조합: {len(conds)}개")

            # apcno 캐시 (성별+나이+직업+운전형태 기준)
            apcno_cache: dict[tuple, str] = {}

            for i, cond in enumerate(conds):
                cache_key = (pdcd, cond["sexCd"], cond["insAge"],
                             cond["ocptCd"], cond["drivTdcd"])

                if cache_key not in apcno_cache:
                    apcno = await create_apcno(pdcd, cond)
                    if not apcno:
                        print(f"  ⚠ apcno 생성 실패 ({cache_key}), 스킵")
                        continue
                    apcno_cache[cache_key] = apcno

                apcno = apcno_cache[cache_key]
                prems = await get_premium(apcno, pdcd, cond, cvr_list)

                err = prems.get("_error")
                if err:
                    print(f"  ⚠ [{i+1}/{len(conds)}] 오류: {err[:80]}")
                    continue

                for cvr_cd, prem in prems.items():
                    all_rows.append({
                        "상품코드":     pdcd,
                        "상품명":       PRODUCTS.get(pdcd, ""),
                        "성별":         cond["sex_nm"],
                        "나이":         cond["insAge"],
                        "직업":         cond["ocptCdNm"],
                        "운전형태":     cond["driv_nm"],
                        "심사고지유형": cond["simsa_nm"],
                        "납입면제":     cond["napim_nm"],
                        "플랜":         cond["plan_nm"],
                        "납기만기":     cond["period_nm"],
                        "담보코드":     cvr_cd,
                        "담보명":       cvr_names.get(cvr_cd, ""),
                        f"보험료(월/{DEFAULT_CVR_AMT_MAN}만원)": prem,
                    })

                if (i + 1) % 50 == 0:
                    save_excel(all_rows, "_partial")
                    print(f"  [{i+1}/{len(conds)}] 중간저장 완료")

            save_excel(all_rows, f"_{pdcd}_partial")

    finally:
        save_excel(all_rows)
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", nargs="+", default=None,
                        help="수집 상품코드 (예: 24953 24954)")
    parser.add_argument("--ages", nargs="+", type=int, default=None,
                        help="수집 나이 목록 (예: 30 40 50)")
    args = parser.parse_args()
    asyncio.run(main(args))
