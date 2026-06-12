# KB 5.10.10 플러스 보험료 raw 응답 확인
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
    ph["pfmFnName"] = fn_name
    ph["pfmGlobalNo"] = ph["pfmTrDate"] = ph["pfmTrTime"] = ""
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
        try {{ return JSON.parse(text); }} catch(e) {{ return {{_raw: text.slice(0,1000)}}; }}
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
    await _page.goto(f"{API_ORIG}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1={pdcd}")
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


async def main():
    global _page

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        _page = await browser.new_page()

        # 실제 24953 보험료 계산으로 현재 세션 동작 확인
        print("▶ 세션 초기화 (24995)...")
        await init_session("24995")

        # 담보 목록 가져오기
        cvr_resp = await _call_api("LTI0100403", {
            "LngtrmNtrpsblCvrInqCndtnInfoDTO": {"pdcd": "24995", "stdt": TODAY, "objctTpcd": "L00001"}
        })
        cvr_items = cvr_resp.get("LngtrmApcCvrInfoPDTO", {}).get("ltApcCvrInfoDTO", [])

        # LB prefix 첫 3개
        lb_cvrs = [c for c in cvr_items if c.get("cvrCd","").startswith("LB")][:3]
        print(f"  LB담보 샘플: {[(c['cvrCd'], c['cvrNm'][:30]) for c in lb_cvrs]}")

        # apcno 생성
        cndtn = {
            "ltictCd": "03", "ltifmCd": "01", "lngtrmContTdcd": "02",
            "pymnPrdYrcnt": None, "pymnPrdYrcntCd": "10", "pymnPrdCfcd": "1",
            "insMtrtyYrcnt": None, "insMtrtyYrcntCd": "10", "insMtrtyCfcd": "1",
            "insPrdYrcnt": None, "pymnCyclCd": "L10", "smplComprPrdtCfcd": "10",
            "ltigenCd": "04", "ltifamCd": None, "ltiordCd": "00",
            "comprDesignCfcd": "05",
        }
        obj = {
            "objctSeq": "1", "objtyCfcd": "L001", "objctTpcd": "L00001",
            "insdpsCncpsSeq": None, "sexCd": "1", "insAge": "45", "fulage": "45",
            "ocptCd": "B014", "ocptCdNm": "전업주부", "rateGrade": "1", "riskGrdCd": "A",
            "jobgrpGrade": "04", "insdpsRlcd": "001", "drivTdcd": "01",
            "objtyInsBgdt": TODAY, "embrYn": "N", "objctSttcd": "01",
            "partyMncnt": "1", "objGuarntPrem": 0,
        }
        comn_i = {
            "wrClsfc": "I", "apcno": None, "apcDay": TODAY, "insBgdt": TODAY,
            "insEnddt": None, "apcSttcd": None, "apcJobKindCfcd": "01",
            "saleChCfcd": "01", "systemChfcd": "23", "pdcd": "24995",
            "prdtClcd": "202", "inputScrenCfcd": "21", "rncvrSptnApplYn": "Y",
        }
        r = await _call_api("LTI0100106", {"LtApcBasicInfoDTO": {
            "ltApcComnDTO": comn_i, "ltApcTreatOrgDTO": dict(_treat_org),
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
        apcno = r.get("ltApcBasicInfoOutDTO", {}).get("ltApcComnDTO", {}).get("apcno")
        print(f"  apcno={apcno}")

        # 보험료 계산 (LB 처음 3개) — raw 응답 전체 출력
        amt = 10_000_000
        batch = []
        for c in lb_cvrs:
            batch.append({
                "objctSeq": "1", "objctTpcd": c.get("objctTpcd", "L00001"),
                "cvrCd": c["cvrCd"], "cvrNm": c["cvrNm"],
                "cvrNtrSeq": c.get("cvrNtrSeq", "1"), "cvrTpcd": c.get("cvrTpcd", ""),
                "cvrNtrCkYn": "1", "ntramtInputYn": c.get("ntramtInputYn", "Y"),
                "pymnPrdInputYn": c.get("pymnPrdInputYn", "N"),
                "insPrdInputYn": c.get("insPrdInputYn", "N"),
                "cvrSuplmtButtonRvtztYn": "N",
                "achngCvrPerpsNtramt": amt, "achngCvrTnthwnUnitNtramt": 1000,
                "cvrAchngCvrNtramt": amt, "cvrFullNm": c.get("cvrFullNm", c["cvrNm"]),
                "ntrpsblCvrTpcd": c.get("ntrpsblCvrTpcd", ""),
                "screnDispOrd": c.get("screnDispOrd", "1"),
            })

        comn_d = dict(comn_i)
        comn_d["wrClsfc"] = "D"
        comn_d["apcno"] = apcno
        comn_d["apcSttcd"] = "00"

        body = {"LngtrmApcRtimePremInqInfoDTO": {
            "rtimeCalYn": "Y",
            "ltApcComnDTO": comn_d,
            "ltApcContCndtnDTO": cndtn,
            "ltApcObjDtlDTO": obj,
            "ltApcCvrPremSuplmtInfoDTO": {},
            "ltApcCvrInfoDTO": batch,
        }}
        resp2 = await _call_api("LTI0103805", body)
        print("\nLTI0103805 raw 응답 (첫 1500자):")
        print(json.dumps(resp2, ensure_ascii=False)[:1500])

        await browser.close()


asyncio.run(main())
