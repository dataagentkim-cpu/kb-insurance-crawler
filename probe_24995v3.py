# KB 5.10.10 플러스 UI 상태 캡처 스크립트 v3
"""
LTI0100106 호출을 직접 시도해서 유효한 납기/만기/심사 조합 탐색
기존 24953 파라미터를 comprDesignCfcd="05"로 바꿔서 어떤 조합이 동작하는지 확인
"""
import asyncio, json
from datetime import date
from pathlib import Path
from playwright.async_api import async_playwright

API_ORIG  = "https://ppa.kbinsure.co.kr"
API_QUERY = "envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON"
TODAY     = date.today().strftime("%Y-%m-%d")
OUT = Path(__file__).parent

_prohead_tpl = {}
_syshead_tpl = {}
_treat_org   = {}
_page        = None


def _make_req_json(fn_name, body):
    ph = dict(_prohead_tpl)
    ph["pfmFnName"]   = fn_name
    ph["pfmGlobalNo"] = ""
    ph["pfmTrDate"]   = ""
    ph["pfmTrTime"]   = ""
    return json.dumps({"PROHEAD": ph, "SYSHEAD": dict(_syshead_tpl), **body}, ensure_ascii=False)


async def _call_api(fn_name, body):
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
        try {{ return JSON.parse(text); }} catch(e) {{ return {{_raw: text.slice(0,300)}}; }}
    }}
    """
    return await _page.evaluate(script) or {}


async def init_session(pdcd):
    global _prohead_tpl, _syshead_tpl, _treat_org, _page

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
    await _page.goto(url)
    await _page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)

    _prohead_tpl.update(captured["PROHEAD"])
    _prohead_tpl["pfmFnCd"] = "CT01_0495M"
    _syshead_tpl.update(captured["SYSHEAD"])

    emp_no = _syshead_tpl.get("pfmEmpNo", "")
    org = captured.get("ORG", {})
    _treat_org.update({
        "usCd": None, "usNm": None, "mngtEmpCd": emp_no,
        "mngtEmpNm": org.get("empNm", ""), "mngtOfcd": None, "mngtOfficeNm": None,
        "mngtBrccd": org.get("brccd", ""), "mngtBrchofNm": org.get("brchofNm", ""),
        "ctcd": org.get("ctcd", ""), "cntrNm": org.get("cntrNm", ""),
        "hqCd": org.get("hqCd", ""), "slctnOrgGrdCd": "02",
        "upOrgChngYn": None, "usInputObjcYn": None, "indcEmpNo": None, "indcNm": None,
    })
    print(f"  세션 초기화 완료 (userId={_prohead_tpl.get('pfmUserId')})")


_NULL_CVR = {"objctSeq":None,"objctTpcd":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"cvrTpcd":None,"mobilCvrTpcd":None,"cvrNtrCkYn":None,"ntramtInputYn":None,"pymnPrdInputYn":None,"insPrdInputYn":None,"cvrDtlInputYn":None,"usePcscrId":None,"cvrSuplmtButtonRvtztYn":None,"achngCvrPerpsNtramt":None,"achngCvrPeraccNtramt":None,"achngCvrTnthwnUnitNtramt":None,"cvrAchngCvrNtramt":None,"cvrAchngInsMtrtyYrcnt":None,"cvrAchngInsMtrtyYrcntCd":None,"cvrAchngInsMtrtyYrcntCdNm":None,"cvrAchngInsMtrtyCfcd":None,"achngInsMtrtyAddtnCd":None,"insMtrtyValue":None,"cvrAchngPymnPrdYrcnt":None,"cvrAchngPymnPrdYrcntCd":None,"cvrAchngPymnPrdYrcntCdNm":None,"cvrAchngPymnPrdCfcd":None,"cvrAchngInsPrdYrcnt":None,"pymnPrdValue":None,"achngPymnPrdAddtnCd":None,"cvrAchngInsBgdt":None,"cvrAchngInsEnddt":None,"cvrScrenDispOrd":None,"lngtrmUdtmnAcumCcd":None,"achngCvrPrem":None,"premCalYn":None,"basicCvrYn":None,"cvrChrctrCd":None,"rtimePremCalYn":None,"rtimePrem":None,"cvrRnwlCyclCd":None,"insBgdtStingCfcd":None,"insBgdtStingClsfcValue":None,"ntrpsblCvrTpcd":None,"achngStrtRsrvAge":None,"strtRsrvAgeInputYn":None,"achngRsrvCvrPrem":None,"guarntClmrsvCalTpcd":None,"cvrFullNm":None,"bestNtrLimitAmt":None,"cvrPremKey":None,"incproRate":None,"stdUnbodyGrdCd":None,"guarntChrctrCd":None,"screnDispTypeCfcd":None,"rldmgStablDcPrem":None,"embrPrvuseCvrYn":None,"deletedYn":None,"embrCvrPrem":None,"screnDispOrd":None,"upCvrCd":None,"fcastCsmAmt":None,"proftMltpl":None,"embrRldmgStablDcPrem":None,"sametmNtrCfcd":None,"cvrDcAfPrem":None,"cvrInsert":None,"dcicpPrem":None,"stdUnbodyRiskEpnt":None}
_NULL_PRPRT_CVR = {"groupSeq":None,"objctSeq":None,"objctTpcd":None,"objctTypeNm":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"cvrDtlInputYn":None,"cvrNtrCkYn":None,"ntramtInputYn":None,"usePcscrId":None,"cvrSuplmtButtonRvtztYn":None,"cvrAchngInsBgdt":None,"cvrAchngInsEnddt":None,"cvrAchngInsMtrtyYrcnt":None,"cvrAchngInsMtrtyYrcntCd":None,"cvrAchngInsMtrtyYrcntCdNm":None,"cvrAchngInsMtrtyCfcd":None,"cvrAchngPymnPrdYrcnt":None,"cvrAchngPymnPrdYrcntCd":None,"cvrAchngPymnPrdYrcntCdNm":None,"cvrAchngPymnPrdCfcd":None,"cvrAchngInsPrdYrcnt":None,"cvrAchngCvrNtramt":None,"achngCvrTnthwnUnitNtramt":None,"achngCvrPerpsNtramt":None,"achngCvrPeraccNtramt":None,"achngCvrPrem":None,"cvrScrenDispOrd":None,"cvrFullNm":None,"screnDispTypeCfcd":None,"fcastCsmAmt":None,"proftMltpl":None}
_NULL_RATE_FCTR = {"loctSeq":None,"groupSeq":None,"objctSeq":None,"cvrCd":None,"cvrNtrSeq":None,"pdcrtItmId":None,"nmrItmval":None,"charItmval":None}
_NULL_DISBL = {"apcCncpsSeq":None,"custNo":None,"apcCncpsTpcd":None,"disblCfcd":None,"disblValidBgdt":None,"disblValidEnddt":None,"disblScopeCfcd":None}
_NULL_RVW = {"objctSeq":None,"apcno":None,"udtmnVioltYn":None,"udtmnSeq":None,"hmnRvwApplObjcYn":None,"uwObjcCfcd":None,"apcCncpsSeq":None,"partySeq":None,"lngtrmUdtmnDlngCfcd":None,"lngtrmUdtmnDtxt":None,"lngtrmUdtmnId":None,"manualDtlSeq":None,"manualHelpTpcd":None,"ctccBfMngtObjcYn":None,"lngtrmManualClcd":None,"acumStndCfcd":None,"lngtrmUdrtkCvrPurpCd":None,"acumStndSeq":None,"cmmlSeq":None,"lngtrmUdtmnClcd":None,"acumExcsAmt":None,"acumStamt":None,"objctTypeCvrPurpCd":None,"uwDcdarbCd":None,"orgCd":None,"filtrCltrCdLt":None,"lngtrmUdtmnTtxt":None}
_NULL_AUTO_RVW = {"lngtrmUdtmnClcd":None,"udtmnVioltYn":None,"udtmnSeq":None,"hmnRvwApplObjcYn":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"pdcrtItmId":None,"charItmval":None,"prdtManualGroupNo":None,"cmmlSeq":None,"cmmlEcctSeq":None,"pdcrtItmHnglNm":None,"rpsntErrMsgCd":None,"ctCd":None,"apcno":None,"uwDcdarbCd":None,"uwObjcCfcd":None,"apcCncpsSeq":None,"objctSeq":None,"acumExcsAmt":None,"acumStamt":None,"objctTypeCvrPurpCd":None,"orgCd":None,"lngtrmUdtmnDlngCfcd":None,"cvrScrenDispOrd":None,"lngtrmUdtmnDtxt":None,"acumStndCfcd":None,"dlngYn":None,"partySeq":None}


async def try_create_apcno(pdcd, comprDesignCfcd, ltifmCd, pymnPrd, insMtrty, insMtrtyCfcd,
                            ltiordCd="00", ltigenCd="04", lngtrmContTdcd="02"):
    """LTI0100106으로 청약 생성 시도 — 성공 여부와 apcno or 에러코드 반환"""
    cndtn = {
        "ltictCd": "03",
        "ltifmCd": ltifmCd,
        "lngtrmContTdcd": lngtrmContTdcd,
        "pymnPrdYrcnt": None,
        "pymnPrdYrcntCd": pymnPrd,
        "pymnPrdCfcd": "1",
        "insMtrtyYrcnt": None,
        "insMtrtyYrcntCd": insMtrty,
        "insMtrtyCfcd": insMtrtyCfcd,
        "insPrdYrcnt": None,
        "pymnCyclCd": "L10",
        "smplComprPrdtCfcd": "10",
        "ltigenCd": ltigenCd,
        "ltifamCd": None,
        "ltiordCd": ltiordCd,
        "comprDesignCfcd": comprDesignCfcd,
    }
    obj = {
        "objctSeq": "1", "objtyCfcd": "L001", "objctTpcd": "L00001",
        "insdpsCncpsSeq": None,
        "sexCd": "1", "insAge": "45", "fulage": "45",
        "ocptCd": "B014", "ocptCdNm": "전업주부",
        "rateGrade": "1", "riskGrdCd": "A", "jobgrpGrade": "04",
        "insdpsRlcd": "001",
        "drivTdcd": "01",
        "objtyInsBgdt": TODAY,
        "embrYn": "N", "objctSttcd": "01", "partyMncnt": "1", "objGuarntPrem": 0,
    }
    comn = {
        "wrClsfc": "I", "apcno": None, "apcDay": TODAY, "insBgdt": TODAY,
        "insEnddt": None, "apcSttcd": None,
        "apcJobKindCfcd": "01", "saleChCfcd": "01", "systemChfcd": "23",
        "pdcd": pdcd, "prdtClcd": "202", "inputScrenCfcd": "21", "rncvrSptnApplYn": "Y",
    }
    resp = await _call_api("LTI0100106", {"LtApcBasicInfoDTO": {
        "ltApcComnDTO": comn, "ltApcTreatOrgDTO": dict(_treat_org),
        "ltApcPolhdInfoDTO": {}, "ltApcObjDtlDTO": [obj],
        "ltApcContCndtnDTO": cndtn,
        "ltApcDcRateInfoDTO": [], "ltApcCvrInfoDTO": [dict(_NULL_CVR)],
        "ltApcPremDTO": {"acprm": None, "guarntPrem": 0},
        "ltApcBnfcryDTO": {}, "ltApcSettlBkacntDTO": {}, "ltApcPyBkacntDTO": {},
        "ltApcInsdpsSuplmtInfoDTO": [], "ltApcContchngObjcDTO": [],
        "ltApcLoctInfoDTO": [], "ltApcPrprtGroupInfoDTO": [],
        "ltApcNtrPrprtCvrDTO": [dict(_NULL_PRPRT_CVR)],
        "ltApcNtrPrprtEtcCvrDTO": [dict(_NULL_PRPRT_CVR)],
        "ltApcPrprtRateFctrInfoDTO": [dict(_NULL_RATE_FCTR)],
        "ltApcCncpsDisblDeductInfoDTO": [dict(_NULL_DISBL)],
        "ltApcbfContInfoDTO": [], "ltApcCmpanmlInfoDTO": [],
        "etcMaterLngtrmRvwVioltInfoDTO": [dict(_NULL_RVW)],
        "cvrMaterLngtrmRvwVioltInfoDTO": [dict(_NULL_RVW)],
        "lngtrmAutoRvwPDTO": [dict(_NULL_AUTO_RVW)],
    }})
    err = resp.get("ErrorCode", "")
    msg = resp.get("ErrorMsg", "")
    if str(err) == "0":
        apcno = resp.get("ltApcBasicInfoOutDTO", {}).get("ltApcComnDTO", {}).get("apcno")
        return True, apcno, ""
    return False, None, f"{err}: {msg[:80]}"


async def probe_combinations(pdcd, comprDesignCfcd, periods, simsa_options, napim_options, plan_options):
    """여러 조합 시도해서 어떤 것이 유효한지 파악"""
    print(f"\n[{pdcd}] comprDesignCfcd={comprDesignCfcd} 조합 탐색")
    valid = []

    for ltifm, pymn, mtrty, mtrty_cfcd, label in periods:
        for ltiord_cd, ltiord_nm in simsa_options:
            for napim_cd, napim_nm in napim_options:
                for plan_cd, plan_nm in plan_options:
                    ok, apcno, err = await try_create_apcno(
                        pdcd, comprDesignCfcd, ltifm, pymn, mtrty, mtrty_cfcd,
                        ltiordCd=ltiord_cd, ltigenCd=napim_cd, lngtrmContTdcd=plan_cd
                    )
                    marker = "✓" if ok else "✗"
                    print(f"  {marker} {label} | 심사={ltiord_nm} | 납면={napim_nm} | 플랜={plan_nm} | {err if not ok else f'apcno={apcno}'}")
                    if ok:
                        valid.append({
                            "pdcd": pdcd, "comprDesignCfcd": comprDesignCfcd,
                            "ltifmCd": ltifm, "pymnPrdYrcntCd": pymn,
                            "insMtrtyYrcntCd": mtrty, "insMtrtyCfcd": mtrty_cfcd,
                            "period_label": label,
                            "ltiordCd": ltiord_cd, "simsa_nm": ltiord_nm,
                            "ltigenCd": napim_cd, "napim_nm": napim_nm,
                            "lngtrmContTdcd": plan_cd, "plan_nm": plan_nm,
                            "apcno": apcno,
                        })
                    await asyncio.sleep(0.3)
    return valid


async def main():
    global _page

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        _page = await browser.new_page()

        # 세션 초기화 (24995 기준)
        print("▶ 세션 초기화...")
        await init_session("24995")

        # ── 24995 연만기갱신형 탐색 ──────────────────────────────
        # 기존 24953과 유사하게 시도 (ltifmCd, 납기, 만기 조합)
        periods_yr = [
            ("01", "10", "10", "1", "10년납/10년만기"),
            ("02", "15", "15", "1", "15년납/15년만기"),
            ("03", "20", "20", "1", "20년납/20년만기"),
            ("04", "30", "30", "1", "30년납/30년만기"),
            # 가능한 다른 코드들
            ("", "10", "10", "1", "ltifm='' 10년납/10년만기"),
            ("05", "10", "10", "1", "ltifm=05 10년납/10년만기"),
        ]
        # 심사 코드 (기존 24953: "14"=간편3.0.5, "03"=간편3.3.5, "00"=일반)
        simsa = [("00", "일반"), ("14", "간편3.0.5"), ("03", "간편3.3.5")]
        # 납입면제 (기존 24953: "04"=5대, "00"=미적용)
        napim = [("04", "5대납입면제"), ("00", "납입면제미적용")]
        # 플랜 (기존: "01"=간편심사형, "02"=일반심사형, "11"=암동시가입)
        plans_yr = [("02", "일반심사형"), ("01", "간편심사형")]

        valid_24995 = await probe_combinations(
            "24995", "05", periods_yr[:4], simsa[:1], napim[:1], plans_yr
        )

        all_valid = valid_24995

        out = OUT / "probe_24995v3_result.json"
        out.write_text(json.dumps(all_valid, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 유효 조합 {len(all_valid)}개 저장: {out}")

        await browser.close()


asyncio.run(main())
