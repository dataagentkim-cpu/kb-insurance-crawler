# KB 5.10.10 플러스 전체 조합 탐색 v4
"""
24995(연만기갱신형), 24999(세만기) 전체 심사/납면/플랜 조합 탐색
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
    print(f"  세션 OK (userId={_prohead_tpl.get('pfmUserId')})")


_NULL_CVR = {"objctSeq":None,"objctTpcd":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"cvrTpcd":None,"mobilCvrTpcd":None,"cvrNtrCkYn":None,"ntramtInputYn":None,"pymnPrdInputYn":None,"insPrdInputYn":None,"cvrDtlInputYn":None,"usePcscrId":None,"cvrSuplmtButtonRvtztYn":None,"achngCvrPerpsNtramt":None,"achngCvrPeraccNtramt":None,"achngCvrTnthwnUnitNtramt":None,"cvrAchngCvrNtramt":None,"cvrAchngInsMtrtyYrcnt":None,"cvrAchngInsMtrtyYrcntCd":None,"cvrAchngInsMtrtyYrcntCdNm":None,"cvrAchngInsMtrtyCfcd":None,"achngInsMtrtyAddtnCd":None,"insMtrtyValue":None,"cvrAchngPymnPrdYrcnt":None,"cvrAchngPymnPrdYrcntCd":None,"cvrAchngPymnPrdYrcntCdNm":None,"cvrAchngPymnPrdCfcd":None,"cvrAchngInsPrdYrcnt":None,"pymnPrdValue":None,"achngPymnPrdAddtnCd":None,"cvrAchngInsBgdt":None,"cvrAchngInsEnddt":None,"cvrScrenDispOrd":None,"lngtrmUdtmnAcumCcd":None,"achngCvrPrem":None,"premCalYn":None,"basicCvrYn":None,"cvrChrctrCd":None,"rtimePremCalYn":None,"rtimePrem":None,"cvrRnwlCyclCd":None,"insBgdtStingCfcd":None,"insBgdtStingClsfcValue":None,"ntrpsblCvrTpcd":None,"achngStrtRsrvAge":None,"strtRsrvAgeInputYn":None,"achngRsrvCvrPrem":None,"guarntClmrsvCalTpcd":None,"cvrFullNm":None,"bestNtrLimitAmt":None,"cvrPremKey":None,"incproRate":None,"stdUnbodyGrdCd":None,"guarntChrctrCd":None,"screnDispTypeCfcd":None,"rldmgStablDcPrem":None,"embrPrvuseCvrYn":None,"deletedYn":None,"embrCvrPrem":None,"screnDispOrd":None,"upCvrCd":None,"fcastCsmAmt":None,"proftMltpl":None,"embrRldmgStablDcPrem":None,"sametmNtrCfcd":None,"cvrDcAfPrem":None,"cvrInsert":None,"dcicpPrem":None,"stdUnbodyRiskEpnt":None}
_NULL_PRPRT_CVR = {"groupSeq":None,"objctSeq":None,"objctTpcd":None,"objctTypeNm":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"cvrDtlInputYn":None,"cvrNtrCkYn":None,"ntramtInputYn":None,"usePcscrId":None,"cvrSuplmtButtonRvtztYn":None,"cvrAchngInsBgdt":None,"cvrAchngInsEnddt":None,"cvrAchngInsMtrtyYrcnt":None,"cvrAchngInsMtrtyYrcntCd":None,"cvrAchngInsMtrtyYrcntCdNm":None,"cvrAchngInsMtrtyCfcd":None,"cvrAchngPymnPrdYrcnt":None,"cvrAchngPymnPrdYrcntCd":None,"cvrAchngPymnPrdYrcntCdNm":None,"cvrAchngPymnPrdCfcd":None,"cvrAchngInsPrdYrcnt":None,"cvrAchngCvrNtramt":None,"achngCvrTnthwnUnitNtramt":None,"achngCvrPerpsNtramt":None,"achngCvrPeraccNtramt":None,"achngCvrPrem":None,"cvrScrenDispOrd":None,"cvrFullNm":None,"screnDispTypeCfcd":None,"fcastCsmAmt":None,"proftMltpl":None}
_NULL_RATE_FCTR = {"loctSeq":None,"groupSeq":None,"objctSeq":None,"cvrCd":None,"cvrNtrSeq":None,"pdcrtItmId":None,"nmrItmval":None,"charItmval":None}
_NULL_DISBL = {"apcCncpsSeq":None,"custNo":None,"apcCncpsTpcd":None,"disblCfcd":None,"disblValidBgdt":None,"disblValidEnddt":None,"disblScopeCfcd":None}
_NULL_RVW = {"objctSeq":None,"apcno":None,"udtmnVioltYn":None,"udtmnSeq":None,"hmnRvwApplObjcYn":None,"uwObjcCfcd":None,"apcCncpsSeq":None,"partySeq":None,"lngtrmUdtmnDlngCfcd":None,"lngtrmUdtmnDtxt":None,"lngtrmUdtmnId":None,"manualDtlSeq":None,"manualHelpTpcd":None,"ctccBfMngtObjcYn":None,"lngtrmManualClcd":None,"acumStndCfcd":None,"lngtrmUdrtkCvrPurpCd":None,"acumStndSeq":None,"cmmlSeq":None,"lngtrmUdtmnClcd":None,"acumExcsAmt":None,"acumStamt":None,"objctTypeCvrPurpCd":None,"uwDcdarbCd":None,"orgCd":None,"filtrCltrCdLt":None,"lngtrmUdtmnTtxt":None}
_NULL_AUTO_RVW = {"lngtrmUdtmnClcd":None,"udtmnVioltYn":None,"udtmnSeq":None,"hmnRvwApplObjcYn":None,"cvrCd":None,"cvrNm":None,"cvrNtrSeq":None,"pdcrtItmId":None,"charItmval":None,"prdtManualGroupNo":None,"cmmlSeq":None,"cmmlEcctSeq":None,"pdcrtItmHnglNm":None,"rpsntErrMsgCd":None,"ctCd":None,"apcno":None,"uwDcdarbCd":None,"uwObjcCfcd":None,"apcCncpsSeq":None,"objctSeq":None,"acumExcsAmt":None,"acumStamt":None,"objctTypeCvrPurpCd":None,"orgCd":None,"lngtrmUdtmnDlngCfcd":None,"cvrScrenDispOrd":None,"lngtrmUdtmnDtxt":None,"acumStndCfcd":None,"dlngYn":None,"partySeq":None}


async def try_apcno(pdcd, comprDesignCfcd, ltifmCd, pymnPrd, insMtrty, insMtrtyCfcd,
                    ltiordCd="00", ltigenCd="04", lngtrmContTdcd="02", ltifamCd=None):
    cndtn = {
        "ltictCd": "03", "ltifmCd": ltifmCd, "lngtrmContTdcd": lngtrmContTdcd,
        "pymnPrdYrcnt": None, "pymnPrdYrcntCd": pymnPrd, "pymnPrdCfcd": "1",
        "insMtrtyYrcnt": None, "insMtrtyYrcntCd": insMtrty,
        "insMtrtyCfcd": insMtrtyCfcd,
        "insPrdYrcnt": None, "pymnCyclCd": "L10", "smplComprPrdtCfcd": "10",
        "ltigenCd": ltigenCd, "ltifamCd": ltifamCd, "ltiordCd": ltiordCd,
        "comprDesignCfcd": comprDesignCfcd,
    }
    obj = {
        "objctSeq": "1", "objtyCfcd": "L001", "objctTpcd": "L00001",
        "insdpsCncpsSeq": None, "sexCd": "1", "insAge": "45", "fulage": "45",
        "ocptCd": "B014", "ocptCdNm": "전업주부", "rateGrade": "1", "riskGrdCd": "A",
        "jobgrpGrade": "04", "insdpsRlcd": "001", "drivTdcd": "01",
        "objtyInsBgdt": TODAY, "embrYn": "N", "objctSttcd": "01",
        "partyMncnt": "1", "objGuarntPrem": 0,
    }
    comn = {
        "wrClsfc": "I", "apcno": None, "apcDay": TODAY, "insBgdt": TODAY,
        "insEnddt": None, "apcSttcd": None, "apcJobKindCfcd": "01",
        "saleChCfcd": "01", "systemChfcd": "23", "pdcd": pdcd,
        "prdtClcd": "202", "inputScrenCfcd": "21", "rncvrSptnApplYn": "Y",
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
    err = str(resp.get("ErrorCode", ""))
    msg = resp.get("ErrorMsg", "")
    if err == "0":
        apcno = resp.get("ltApcBasicInfoOutDTO", {}).get("ltApcComnDTO", {}).get("apcno")
        return True, apcno, ""
    return False, None, f"{err}: {msg[:60]}"


async def scan(pdcd, comprDesignCfcd, periods, sims, napims, plans):
    results = {}
    for ltifm, pymn, mtrty, mcfcd, plabel in periods:
        for sc, sn in sims:
            for nc, nn in napims:
                for pc, pn in plans:
                    key = f"{plabel}|심사={sn}|납면={nn}|플랜={pn}"
                    ok, apcno, err = await try_apcno(pdcd, comprDesignCfcd, ltifm, pymn, mtrty, mcfcd,
                                                      ltiordCd=sc, ltigenCd=nc, lngtrmContTdcd=pc)
                    marker = "✓" if ok else "✗"
                    short_err = f" → {err}" if not ok else f" → {apcno}"
                    print(f"  {marker} {key}{short_err}")
                    results[key] = {"ok": ok, "apcno": apcno, "err": err,
                                    "pdcd": pdcd, "comprDesignCfcd": comprDesignCfcd,
                                    "ltifmCd": ltifm, "pymnPrdYrcntCd": pymn,
                                    "insMtrtyYrcntCd": mtrty, "insMtrtyCfcd": mcfcd,
                                    "ltiordCd": sc, "ltigenCd": nc, "lngtrmContTdcd": pc}
                    await asyncio.sleep(0.2)
    return results


async def main():
    global _page

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        _page = await browser.new_page()

        print("▶ 세션 초기화...")
        await init_session("24995")

        all_results = {}

        # ── 24995 연만기갱신형 ──────────────────────────────────
        print("\n=== 24995 (연만기갱신형) ===")
        periods_yr = [
            ("01", "10", "10", "1", "10년납/10년만기"),
            ("02", "15", "15", "1", "15년납/15년만기"),
            ("03", "20", "20", "1", "20년납/20년만기"),
            ("04", "30", "30", "1", "30년납/30년만기"),
        ]
        sims = [("00", "일반"), ("14", "간편3.0.5"), ("03", "간편3.3.5")]
        napims = [("04", "5대납면"), ("00", "납면미적용"), ("11", "6대납면"), ("14", "1대납면")]
        plans = [("01", "간편심사형"), ("02", "일반심사형"), ("11", "암동시가입")]

        r = await scan("24995", "05", periods_yr[:1], sims, napims, plans)
        all_results["24995"] = r

        # ── 24999 세만기 ──────────────────────────────────────
        print("\n=== 24999 (세만기) ===")
        periods_se = [
            ("01", "10", "90", "2", "10년납/90세만기"),
            ("01", "10", "95", "2", "10년납/95세만기"),
            ("01", "10", "A0", "2", "10년납/100세만기"),
            ("02", "15", "90", "2", "15년납/90세만기"),
            ("03", "20", "90", "2", "20년납/90세만기"),
            ("04", "30", "90", "2", "30년납/90세만기"),
        ]

        r2 = await scan("24999", "05", periods_se[:1], sims, napims[:2], plans)
        all_results["24999"] = r2

        out = OUT / "probe_24995v4_result.json"
        out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

        # 요약
        for pdcd, res in all_results.items():
            ok_keys = [k for k, v in res.items() if v["ok"]]
            print(f"\n[{pdcd}] 유효 조합 {len(ok_keys)}개:")
            for k in ok_keys[:10]:
                print(f"  {k}")

        await browser.close()


asyncio.run(main())
