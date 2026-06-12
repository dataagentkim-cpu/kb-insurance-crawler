"""
KB손해보험 보험료 수집기

실행:
  python3 kb_collect.py --products 24953          # 연만기 표준
  python3 kb_collect.py --products 24953 24954    # 연만기 전체
  python3 kb_collect.py --products 24957 24958    # 세만기 전체
  python3 kb_collect.py --ages 30 40 50           # 특정 나이

결과: kb_보험료_YYYYMMDD_<pdcd>.xlsx
"""
import asyncio, json, argparse
from datetime import date
from pathlib import Path
import pandas as pd
from playwright.async_api import async_playwright

TODAY     = date.today().strftime("%Y-%m-%d")
TODAY_NUM = date.today().strftime("%Y%m%d")
ROOT      = Path(__file__).parent
API_QUERY = "envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON"
API_ORIG  = "https://ppa.kbinsure.co.kr"

# ── 상품별 설정 ──────────────────────────────────────────────
# periods 튜플: (ltifmCd, pymnPrdYrcntCd, insMtrtyYrcntCd, insMtrtyCfcd, label)
#   연만기: insMtrtyCfcd="1" (년 단위), 세만기: insMtrtyCfcd="2" (세 단위)
_SE_PERIODS = [
    ("01", "10", "90", "2", "10년납/90세만기"),
    ("01", "10", "95", "2", "10년납/95세만기"),
    ("01", "10", "A0", "2", "10년납/100세만기"),
    ("02", "15", "90", "2", "15년납/90세만기"),
    ("02", "15", "95", "2", "15년납/95세만기"),
    ("02", "15", "A0", "2", "15년납/100세만기"),
    ("03", "20", "90", "2", "20년납/90세만기"),
    ("03", "20", "95", "2", "20년납/95세만기"),
    ("03", "20", "A0", "2", "20년납/100세만기"),
    ("",   "25", "90", "2", "25년납/90세만기"),
    ("",   "25", "95", "2", "25년납/95세만기"),
    ("",   "25", "A0", "2", "25년납/100세만기"),
    ("04", "30", "90", "2", "30년납/90세만기"),
    ("04", "30", "95", "2", "30년납/95세만기"),
    ("04", "30", "A0", "2", "30년납/100세만기"),
]

PRODUCT_CONFIGS = {
    "24953": {
        "name":           "연만기갱신형(표준)",
        "comprDesignCfcd":"01",
        "napim":          [("04", "5대납입면제기본형"), ("00", "납입면제미적용형")],
        "periods":        [("01","10","10","1","10년납/10년만기"),
                           ("02","15","15","1","15년납/15년만기"),
                           ("03","20","20","1","20년납/20년만기"),
                           ("04","30","30","1","30년납/30년만기")],
        "excl_renewal":   False,   # 갱신형 포함
    },
    "24954": {
        "name":           "연만기갱신형(해약환급금미지급형)",
        "comprDesignCfcd":"04",
        "ltifamCd":       "07",   # 전기간 미지급형 — 필수
        "napim":          [("14", "1대납입면제기본형"), ("11", "6대납입면제기본형")],
        "periods":        [("10","10","10","1","10년납/10년만기"),
                           ("02","15","15","1","15년납/15년만기"),
                           ("03","20","20","1","20년납/20년만기"),
                           ("04","30","30","1","30년납/30년만기")],
        "excl_renewal":   False,
    },
    "24957": {
        "name":           "세만기(표준)",
        "comprDesignCfcd":"01",
        "napim":          [("04", "5대납입면제기본형"), ("00", "납입면제미적용형")],
        "periods":        _SE_PERIODS,
        "excl_renewal":   True,    # 갱신형 제외
    },
    "24958": {
        "name":           "세만기(해약환급금미지급형)",
        "comprDesignCfcd":"04",
        "ltifamCd":       "07",   # 전기간 미지급형 — 필수
        "napim":          [("11", "6대납입면제기본형"), ("14", "1대납입면제기본형")],
        "periods":        _SE_PERIODS,
        "excl_renewal":   True,
    },
    # ── KB 5.10.10 플러스 (맞춤고지방식) ──────────────────────────
    # 24953/57 계열과 구조가 다름: 담보가 전부 LB(맞춤고지) 하나뿐이라
    # 간편/일반 심사 구분도, 납입면제 리더(rider)도 없다.
    # 보험료가 산출되는 유일한 경로:
    #   comprDesignCfcd="05"(맞춤고지) · ltiordCd="00" · ltigenCd="00"(납면미적용)
    # comprDesignCfcd("05"/"01"/"04")·plan(lngtrmContTdcd)은 보험료에 영향 없음 → 고정.
    # 그래서 simsa/napim/plans 를 각각 1개로 override 해 단일 경로만 순회한다.
    "24995": {
        "name":           "연만기갱신형(맞춤고지)",
        "comprDesignCfcd":"05",
        "napim":          [("00", "납입면제미적용형")],            # ltigenCd="00" 만 유효
        "simsa":          [("00", "맞춤고지")],                    # ltiordCd="00" 만 유효 → LB prefix
        "plans":          [("02", "맞춤고지형")],                  # 보험료 무관, 중복 방지용 단일값
        "periods":        [("01", "10", "10", "1", "10년납/10년만기(갱신형)"),
                           ("03", "20", "20", "1", "20년납/20년만기(갱신형)"),
                           ("04", "30", "30", "1", "30년납/30년만기(갱신형)")],
        "excl_renewal":   False,   # 담보가 전부 갱신형 — 제외하면 안 됨
        # 배치로 보내면 상호배타 담보끼리 서로 null 처리됨(배치20=200개·배치1=384개).
        # 기본 사망/후유장해까지 빠지므로 담보별 단독 산출(배치1)로 정확도 확보.
        "batch_size":     1,
    },
}

# ── 공통 상수 ─────────────────────────────────────────────────
SIMSA = [
    ("14", "간편심사(3.0.5)"),
    ("03", "간편심사(3.3.5)"),
    ("00", "일반심사"),
]

PLAN = [
    ("01", "간편심사형"),
    ("11", "암동시가입"),
    ("02", "일반심사형"),
]

# 심사고지유형 → 허용 플랜
SIMSA_PLAN_ALLOW = {
    "14": {"01", "11"}, "15": {"01", "11"}, "16": {"01", "11"},
    "03": {"01", "11"}, "17": {"01", "11"}, "04": {"01", "11"},
    "00": {"02"},
}

# 납입면제 → 허용 플랜
NAPIM_PLAN_ALLOW = {
    "04": {"01", "02", "11"}, "00": {"01", "02", "04", "11"},
    "14": {"01", "02", "11"}, "11": {"01", "02", "11"},
}

SEXES       = [("1", "남"), ("2", "여")]
OCCUPATIONS = [
    ("B014", "전업주부", "1", "A", "04"),
]
DRIVS = [("01", "자가용"), ("03", "비운전자형")]

DEFAULT_CVR_AMT_MAN = 1000   # 1,000만원
BATCH_SIZE  = 20
CONCURRENCY = 10

# ── 세션 전역 상태 ─────────────────────────────────────────────
_prohead_tpl: dict = {}
_syshead_tpl: dict = {}
_treat_org:   dict = {}
_page               = None


def _make_req_json(fn_name: str, body: dict) -> str:
    ph = dict(_prohead_tpl)
    ph["pfmFnName"]    = fn_name
    ph["pfmGlobalNo"]  = ""
    ph["pfmTrDate"]    = ""
    ph["pfmTrTime"]    = ""
    return json.dumps({"PROHEAD": ph, "SYSHEAD": dict(_syshead_tpl), **body},
                      ensure_ascii=False)


async def _call_api(fn_name: str, body: dict, _retries: int = 3) -> dict:
    url = f"{API_ORIG}/po-21/APP_EG/SG_EG/WS/v1/APP_KI/DEVON/{fn_name}?{API_QUERY}"
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
    for attempt in range(_retries):
        try:
            return await _page.evaluate(script) or {}
        except Exception as e:
            if attempt < _retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  ⚠ {fn_name} fetch 실패 (시도 {attempt+1}/{_retries}), {wait}초 후 재시도: {e}")
                await asyncio.sleep(wait)
            else:
                raise
    return {}


async def init_session(pdcd: str):
    """브라우저 열기 + PROHEAD/SYSHEAD/TreatOrg 캡처"""
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
                if ph:
                    captured["PROHEAD"] = ph
                    captured["SYSHEAD"] = body.get("SYSHEAD", {})
            elif "getUpOrgInfoByEmpNo" in resp.url and "ORG" not in captured:
                body = await resp.json()
                captured["ORG"] = body.get("EmpOrgDTO", {})
        except Exception:
            pass

    _page.on("response", on_response)

    url = f"{API_ORIG}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1={pdcd}"
    print(f"▶ 세션 초기화 ({pdcd})...")
    await _page.goto(url)
    await _page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)

    if not captured.get("PROHEAD"):
        raise RuntimeError("PROHEAD 캡처 실패")

    _prohead_tpl = captured["PROHEAD"]
    _prohead_tpl["pfmFnCd"] = "CT01_0495M"
    _syshead_tpl = captured["SYSHEAD"]

    emp_no = _syshead_tpl.get("pfmEmpNo", "")
    org = captured.get("ORG", {})
    _treat_org = {
        "usCd": None, "usNm": None, "mngtEmpCd": emp_no,
        "mngtEmpNm": org.get("empNm", ""), "mngtOfcd": None, "mngtOfficeNm": None,
        "mngtBrccd": org.get("brccd", ""), "mngtBrchofNm": org.get("brchofNm", ""),
        "ctcd": org.get("ctcd", ""), "cntrNm": org.get("cntrNm", ""),
        "hqCd": org.get("hqCd", ""), "slctnOrgGrdCd": "02",
        "upOrgChngYn": None, "usInputObjcYn": None, "indcEmpNo": None, "indcNm": None,
    }
    print(f"  ✓ 세션 (userId={_prohead_tpl.get('pfmUserId')}, empNo={emp_no})")
    return browser


async def get_coverage_list(pdcd: str) -> list[dict]:
    """LTI0100403: 담보 목록 조회"""
    resp = await _call_api("LTI0100403", {
        "LngtrmNtrpsblCvrInqCndtnInfoDTO": {"pdcd": pdcd, "stdt": TODAY, "objctTpcd": "L00001"}
    })
    items = resp.get("LngtrmApcCvrInfoPDTO", {}).get("ltApcCvrInfoDTO", [])
    print(f"  담보 목록({pdcd}): {len(items)}개")
    return items


# ── Null placeholder 상수 (WebSquare 빈 리스트용) ──────────────
_NULL_CVR = {"objctSeq":None,"objctTpcd":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"cvrTpcd":None,"mobilCvrTpcd":None,"cvrNtrCkYn":None,"ntramtInputYn":None,"pymnPrdInputYn":None,"insPrdInputYn":None,"cvrDtlInputYn":None,"usePcscrId":None,"cvrSuplmtButtonRvtztYn":None,"achngCvrPerpsNtramt":None,"achngCvrPeraccNtramt":None,"achngCvrTnthwnUnitNtramt":None,"cvrAchngCvrNtramt":None,"cvrAchngInsMtrtyYrcnt":None,"cvrAchngInsMtrtyYrcntCd":None,"cvrAchngInsMtrtyYrcntCdNm":None,"cvrAchngInsMtrtyCfcd":None,"achngInsMtrtyAddtnCd":None,"insMtrtyValue":None,"cvrAchngPymnPrdYrcnt":None,"cvrAchngPymnPrdYrcntCd":None,"cvrAchngPymnPrdYrcntCdNm":None,"cvrAchngPymnPrdCfcd":None,"cvrAchngInsPrdYrcnt":None,"pymnPrdValue":None,"achngPymnPrdAddtnCd":None,"cvrAchngInsBgdt":None,"cvrAchngInsEnddt":None,"cvrScrenDispOrd":None,"lngtrmUdtmnAcumCcd":None,"achngCvrPrem":None,"premCalYn":None,"basicCvrYn":None,"cvrChrctrCd":None,"rtimePremCalYn":None,"rtimePrem":None,"cvrRnwlCyclCd":None,"insBgdtStingCfcd":None,"insBgdtStingClsfcValue":None,"ntrpsblCvrTpcd":None,"achngStrtRsrvAge":None,"strtRsrvAgeInputYn":None,"achngRsrvCvrPrem":None,"guarntClmrsvCalTpcd":None,"cvrFullNm":None,"bestNtrLimitAmt":None,"cvrPremKey":None,"incproRate":None,"stdUnbodyGrdCd":None,"guarntChrctrCd":None,"screnDispTypeCfcd":None,"rldmgStablDcPrem":None,"embrPrvuseCvrYn":None,"deletedYn":None,"embrCvrPrem":None,"screnDispOrd":None,"upCvrCd":None,"fcastCsmAmt":None,"proftMltpl":None,"embrRldmgStablDcPrem":None,"sametmNtrCfcd":None,"cvrDcAfPrem":None,"cvrInsert":None,"dcicpPrem":None,"stdUnbodyRiskEpnt":None}
_NULL_PRPRT_CVR = {"groupSeq":None,"objctSeq":None,"objctTpcd":None,"objctTypeNm":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"cvrDtlInputYn":None,"cvrNtrCkYn":None,"ntramtInputYn":None,"usePcscrId":None,"cvrSuplmtButtonRvtztYn":None,"cvrAchngInsBgdt":None,"cvrAchngInsEnddt":None,"cvrAchngInsMtrtyYrcnt":None,"cvrAchngInsMtrtyYrcntCd":None,"cvrAchngInsMtrtyYrcntCdNm":None,"cvrAchngInsMtrtyCfcd":None,"cvrAchngPymnPrdYrcnt":None,"cvrAchngPymnPrdYrcntCd":None,"cvrAchngPymnPrdYrcntCdNm":None,"cvrAchngPymnPrdCfcd":None,"cvrAchngInsPrdYrcnt":None,"cvrAchngCvrNtramt":None,"achngCvrTnthwnUnitNtramt":None,"achngCvrPerpsNtramt":None,"achngCvrPeraccNtramt":None,"achngCvrPrem":None,"cvrScrenDispOrd":None,"cvrFullNm":None,"screnDispTypeCfcd":None,"fcastCsmAmt":None,"proftMltpl":None}
_NULL_RATE_FCTR = {"loctSeq":None,"groupSeq":None,"objctSeq":None,"cvrCd":None,"cvrNtrSeq":None,"pdcrtItmId":None,"nmrItmval":None,"charItmval":None}
_NULL_DISBL = {"apcCncpsSeq":None,"custNo":None,"apcCncpsTpcd":None,"disblCfcd":None,"disblValidBgdt":None,"disblValidEnddt":None,"disblScopeCfcd":None}
_NULL_RVW = {"objctSeq":None,"apcno":None,"udtmnVioltYn":None,"udtmnSeq":None,"hmnRvwApplObjcYn":None,"uwObjcCfcd":None,"apcCncpsSeq":None,"partySeq":None,"lngtrmUdtmnDlngCfcd":None,"lngtrmUdtmnDtxt":None,"lngtrmUdtmnId":None,"manualDtlSeq":None,"manualHelpTpcd":None,"ctccBfMngtObjcYn":None,"lngtrmManualClcd":None,"acumStndCfcd":None,"lngtrmUdrtkCvrPurpCd":None,"acumStndSeq":None,"cmmlSeq":None,"lngtrmUdtmnClcd":None,"acumExcsAmt":None,"acumStamt":None,"objctTypeCvrPurpCd":None,"uwDcdarbCd":None,"orgCd":None,"filtrCltrCdLt":None,"lngtrmUdtmnTtxt":None}
_NULL_AUTO_RVW = {"lngtrmUdtmnClcd":None,"udtmnVioltYn":None,"udtmnSeq":None,"hmnRvwApplObjcYn":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"pdcrtItmId":None,"charItmval":None,"prdtManualGroupNo":None,"cmmlSeq":None,"cmmlEcctSeq":None,"pdcrtItmHnglNm":None,"rpsntErrMsgCd":None,"ctCd":None,"apcno":None,"uwDcdarbCd":None,"uwObjcCfcd":None,"apcCncpsSeq":None,"objctSeq":None,"acumExcsAmt":None,"acumStamt":None,"objctTypeCvrPurpCd":None,"orgCd":None,"lngtrmUdtmnDlngCfcd":None,"cvrScrenDispOrd":None,"lngtrmUdtmnDtxt":None,"acumStndCfcd":None,"dlngYn":None,"partySeq":None}


def _make_comnDTO(pdcd: str, apcno, wrcls: str) -> dict:
    return {
        "wrClsfc": wrcls, "apcno": apcno, "apcDay": TODAY, "insBgdt": TODAY,
        "insEnddt": None, "apcSttcd": None if wrcls == "I" else "00",
        "apcJobKindCfcd": "01", "saleChCfcd": "01", "systemChfcd": "23",
        "pdcd": pdcd, "prdtClcd": "202", "inputScrenCfcd": "21", "rncvrSptnApplYn": "Y",
    }


def _make_cndtnDTO(cfg: dict, cond: dict) -> dict:
    """상품 config + 조건에서 ltApcContCndtnDTO 생성"""
    return {
        "ltictCd":          "03",
        "ltifmCd":          cond.get("ltifmCd", ""),
        "lngtrmContTdcd":   cond.get("lngtrmContTdcd", "01"),
        "pymnPrdYrcnt":     None,
        "pymnPrdYrcntCd":   cond.get("pymnPrdYrcntCd", "10"),
        "pymnPrdCfcd":      "1",
        "insMtrtyYrcnt":    None,
        "insMtrtyYrcntCd":  cond.get("insMtrtyYrcntCd", "10"),
        "insMtrtyCfcd":     cond.get("insMtrtyCfcd", "1"),
        "insPrdYrcnt":      None,
        "pymnCyclCd":       "L10",
        "smplComprPrdtCfcd":"10",
        "ltigenCd":         cond.get("ltigenCd", "04"),
        "ltifamCd":         cfg.get("ltifamCd"),
        "ltiordCd":         cond.get("ltiordCd", "14"),
        "comprDesignCfcd":  cfg["comprDesignCfcd"],
    }


def _make_objDTO(cond: dict) -> dict:
    return {
        "objctSeq": "1", "objtyCfcd": "L001", "objctTpcd": "L00001",
        "insdpsCncpsSeq": None,
        "sexCd":       cond["sexCd"],
        "insAge":      str(cond["insAge"]),
        "fulage":      str(cond["insAge"]),
        "ocptCd":      cond["ocptCd"],
        "ocptCdNm":    cond["ocptCdNm"],
        "rateGrade":   cond["rateGrade"],
        "riskGrdCd":   cond["riskGrdCd"],
        "jobgrpGrade": cond["jobgrpGrade"],
        "insdpsRlcd":  "001",
        "drivTdcd":    cond["drivTdcd"],
        "objtyInsBgdt":TODAY,
        "embrYn": "N", "objctSttcd": "01", "partyMncnt": "1", "objGuarntPrem": 0,
    }


async def create_apcno(pdcd: str, cfg: dict, cond: dict) -> str | None:
    """LTI0100106: 청약 생성 → apcno"""
    resp = await _call_api("LTI0100106", {"LtApcBasicInfoDTO": {
        "ltApcComnDTO":                 _make_comnDTO(pdcd, None, "I"),
        "ltApcTreatOrgDTO":             dict(_treat_org),
        "ltApcPolhdInfoDTO":            {},
        "ltApcObjDtlDTO":               [_make_objDTO(cond)],
        "ltApcContCndtnDTO":            _make_cndtnDTO(cfg, cond),
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
    }})
    err = resp.get("ErrorCode", "")
    if str(err) != "0":
        print(f"  ⚠ LTI0100106 오류 ({err}): {resp.get('ErrorMsg','')}")
        return None
    return resp.get("ltApcBasicInfoOutDTO", {}).get("ltApcComnDTO", {}).get("apcno")


async def _call_prem_batch(apcno: str, pdcd: str, cfg: dict, cond: dict, batch: list[dict]) -> dict:
    body = {"LngtrmApcRtimePremInqInfoDTO": {
        "rtimeCalYn": "Y",
        "ltApcComnDTO":           _make_comnDTO(pdcd, apcno, "D"),
        "ltApcContCndtnDTO":      _make_cndtnDTO(cfg, cond),
        "ltApcObjDtlDTO":         _make_objDTO(cond),
        "ltApcCvrPremSuplmtInfoDTO": {},
        "ltApcCvrInfoDTO":        batch,
    }}
    resp = await _call_api("LTI0103805", body)
    err = resp.get("ErrorCode", "")
    if str(err) != "0":
        return {"_error": resp.get("ErrorMsg", str(err))}
    out = resp.get("LTI0103805_O", {})
    items = out.get("ltApcCvrInfoDTO", [])
    if not isinstance(items, list):
        items = [items]
    result = {}
    for item in items:
        cd   = item.get("cvrCd", "")
        prem = item.get("achngCvrPrem")
        if cd and prem is not None:
            result[cd] = int(prem)
    return result


async def get_premium(apcno: str, pdcd: str, cfg: dict, cond: dict, cvr_list: list[dict]) -> dict:
    """LTI0103805 병렬 배치로 담보별 보험료 조회"""
    excl_renewal = cfg.get("excl_renewal", False)
    ltiord = cond.get("ltiordCd", "14")

    if ltiord == "00":
        prefix_ok = lambda cd: cd.startswith("LB")
    else:
        prefix_ok = lambda cd: cd.startswith("LE")

    amt  = DEFAULT_CVR_AMT_MAN * 10000
    unit = DEFAULT_CVR_AMT_MAN

    send_cvrs = []
    for cvr in cvr_list:
        cd  = cvr.get("cvrCd", "")
        nm  = cvr.get("cvrNm", "")
        if not prefix_ok(cd):
            continue
        if excl_renewal and "갱신형" in nm:
            continue
        send_cvrs.append({
            "objctSeq": "1",
            "objctTpcd": cvr.get("objctTpcd", "L00001"),
            "cvrCd": cd, "cvrNm": nm,
            "cvrNtrSeq": cvr.get("cvrNtrSeq", "1"),
            "cvrTpcd":   cvr.get("cvrTpcd", ""),
            "cvrNtrCkYn": "1",
            "ntramtInputYn":       cvr.get("ntramtInputYn", "Y"),
            "pymnPrdInputYn":      cvr.get("pymnPrdInputYn", "N"),
            "insPrdInputYn":       cvr.get("insPrdInputYn", "N"),
            "cvrSuplmtButtonRvtztYn": "N",
            "achngCvrPerpsNtramt":     amt,
            "achngCvrTnthwnUnitNtramt": unit,
            "cvrAchngCvrNtramt":       amt,
            "cvrFullNm":   cvr.get("cvrFullNm", nm),
            "ntrpsblCvrTpcd": cvr.get("ntrpsblCvrTpcd", ""),
            "screnDispOrd":   cvr.get("screnDispOrd", "1"),
        })

    if not send_cvrs:
        return {}

    batch_size = cfg.get("batch_size", BATCH_SIZE)
    batches = [send_cvrs[i:i+batch_size] for i in range(0, len(send_cvrs), batch_size)]
    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded(batch):
        async with sem:
            return await _call_prem_batch(apcno, pdcd, cfg, cond, batch)

    results = await asyncio.gather(*[bounded(b) for b in batches])
    combined = {}
    for r in results:
        if "_error" in r:
            return r
        combined.update(r)
    return combined


def build_conditions(pdcd: str, cfg: dict, ages: list[int]) -> list[dict]:
    """조건 조합 목록 생성"""
    conds = []
    napim_list = cfg["napim"]
    simsa_list = cfg.get("simsa", SIMSA)   # 상품별 심사고지유형 override (기본: 전역 SIMSA)
    plan_list  = cfg.get("plans", PLAN)    # 상품별 플랜 override (기본: 전역 PLAN)

    for sex_cd, sex_nm in SEXES:
        for age in ages:
            for ocpt_cd, ocpt_nm, rg, rc, jg in OCCUPATIONS:
                for driv_cd, driv_nm in DRIVS:
                    for simsa_cd, simsa_nm in simsa_list:
                        for napim_cd, napim_nm in napim_list:
                            for plan_cd, plan_nm in plan_list:
                                allowed = (SIMSA_PLAN_ALLOW.get(simsa_cd, set()) &
                                           NAPIM_PLAN_ALLOW.get(napim_cd, set()))
                                if plan_cd not in allowed:
                                    continue
                                for period in cfg["periods"]:
                                    ltifm, pymn, mtrty, mtrty_cfcd, period_nm = period
                                    conds.append({
                                        "pdcd":            pdcd,
                                        "sexCd":           sex_cd,
                                        "sex_nm":          sex_nm,
                                        "insAge":          age,
                                        "ocptCd":          ocpt_cd,
                                        "ocptCdNm":        ocpt_nm,
                                        "rateGrade":       rg,
                                        "riskGrdCd":       rc,
                                        "jobgrpGrade":     jg,
                                        "drivTdcd":        driv_cd,
                                        "driv_nm":         driv_nm,
                                        "ltiordCd":        simsa_cd,
                                        "simsa_nm":        simsa_nm,
                                        "ltigenCd":        napim_cd,
                                        "napim_nm":        napim_nm,
                                        "lngtrmContTdcd":  plan_cd,
                                        "plan_nm":         plan_nm,
                                        "ltifmCd":         ltifm,
                                        "pymnPrdYrcntCd":  pymn,
                                        "insMtrtyYrcntCd": mtrty,
                                        "insMtrtyCfcd":    mtrty_cfcd,
                                        "period_nm":       period_nm,
                                    })
    return conds


def save_excel(rows: list[dict], path: Path):
    if not rows:
        return
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)
    print(f"  ✅ 저장: {path} ({len(df):,}행)")


async def collect_product(pdcd: str, ages: list[int], all_rows: list[dict]):
    """단일 상품 수집"""
    cfg = PRODUCT_CONFIGS[pdcd]
    print(f"\n▶ 상품 {pdcd} ({cfg['name']})")

    cvr_list  = await get_coverage_list(pdcd)
    cvr_names = {c["cvrCd"]: c["cvrNm"] for c in cvr_list}
    conds     = build_conditions(pdcd, cfg, ages)
    print(f"  조건 조합: {len(conds)}개")

    apcno_cache: dict[tuple, str] = {}
    partial_path = ROOT / f"kb_보험료_{TODAY_NUM}_{pdcd}_partial.xlsx"

    for i, cond in enumerate(conds):
        cache_key = (pdcd, cond["sexCd"], cond["insAge"], cond["ocptCd"], cond["drivTdcd"])

        if cache_key not in apcno_cache:
            apcno = await create_apcno(pdcd, cfg, cond)
            if not apcno:
                print(f"  ⚠ apcno 생성 실패 {cache_key}, 스킵")
                continue
            apcno_cache[cache_key] = apcno

        apcno = apcno_cache[cache_key]
        prems = await get_premium(apcno, pdcd, cfg, cond, cvr_list)

        err = prems.get("_error")
        if err:
            print(f"  ⚠ [{i+1}/{len(conds)}] {err[:80]}")
            continue

        for cvr_cd, prem in prems.items():
            all_rows.append({
                "상품코드":     pdcd,
                "상품명":       cfg["name"],
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
            save_excel(all_rows, partial_path)
            print(f"  [{i+1}/{len(conds)}] 중간저장 완료")

    save_excel(all_rows, partial_path)
    print(f"  ▶ 상품 {pdcd} 완료 ({len(all_rows):,}행 누적)")


async def main(args):
    target_pdcds = args.products or list(PRODUCT_CONFIGS.keys())
    ages = args.ages or list(range(20, 71, 5))

    # 세션은 첫 번째 상품으로 초기화
    browser = await init_session(target_pdcds[0])
    all_rows: list[dict] = []

    try:
        for pdcd in target_pdcds:
            await collect_product(pdcd, ages, all_rows)

        # 최종 통합 파일
        if all_rows:
            out = ROOT / f"kb_보험료_{TODAY_NUM}.xlsx"
            save_excel(all_rows, out)
    finally:
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", nargs="+", default=None)
    parser.add_argument("--ages", nargs="+", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(main(args))
