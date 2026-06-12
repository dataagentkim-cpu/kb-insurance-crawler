# 24999 — comprDesignCfcd 스윕 + LA(세만기) vs LB(갱신형) 분리 테스트
import asyncio, json, sys, io
from datetime import date
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API_ORIG="https://ppa.kbinsure.co.kr"; API_QUERY="envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON"
TODAY=date.today().strftime("%Y-%m-%d"); PDCD="24999"
_prohead_tpl={}; _syshead_tpl={}; _treat_org={}; _page=None
from probe_24995v6 import (_NULL_CVR,_NULL_PRPRT_CVR,_NULL_RATE_FCTR,_NULL_DISBL,_NULL_RVW,_NULL_AUTO_RVW)
def _mrj(fn,body):
    ph=dict(_prohead_tpl); ph["pfmFnName"]=fn; ph["pfmGlobalNo"]=ph["pfmTrDate"]=ph["pfmTrTime"]=""
    return json.dumps({"PROHEAD":ph,"SYSHEAD":dict(_syshead_tpl),**body},ensure_ascii=False)
async def _call(fn,body):
    url=f"{API_ORIG}/po-21/APP_EG/SG_EG/WS/v1/APP_KI/DEVON/{fn}?{API_QUERY}"; rj=_mrj(fn,body)
    s=f"""async()=>{{const r=await fetch({json.dumps(url)},{{method:'POST',headers:{{'Content-Type':'application/json'}},body:{json.dumps(rj)}}});const t=await r.text();try{{return JSON.parse(t)}}catch(e){{return{{_raw:t.slice(0,300)}}}}}}"""
    return await _page.evaluate(s) or {}
async def init_session(pdcd):
    cap={}
    async def on_r(resp):
        try:
            if "LTI0102102" in resp.url and "PROHEAD" not in cap:
                b=await resp.json()
                if b.get("PROHEAD"): cap["PROHEAD"]=b["PROHEAD"]; cap["SYSHEAD"]=b.get("SYSHEAD",{})
            elif "getUpOrgInfoByEmpNo" in resp.url and "ORG" not in cap:
                cap["ORG"]=(await resp.json()).get("EmpOrgDTO",{})
        except: pass
    _page.on("response",on_r)
    await _page.goto(f"{API_ORIG}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1={pdcd}")
    await _page.wait_for_load_state("networkidle"); await asyncio.sleep(2)
    _prohead_tpl.update(cap["PROHEAD"]); _prohead_tpl["pfmFnCd"]="CT01_0495M"; _syshead_tpl.update(cap["SYSHEAD"])
    e=_syshead_tpl.get("pfmEmpNo",""); o=cap.get("ORG",{})
    _treat_org.update({"usCd":None,"usNm":None,"mngtEmpCd":e,"mngtEmpNm":o.get("empNm",""),"mngtOfcd":None,"mngtOfficeNm":None,"mngtBrccd":o.get("brccd",""),"mngtBrchofNm":o.get("brchofNm",""),"ctcd":o.get("ctcd",""),"cntrNm":o.get("cntrNm",""),"hqCd":o.get("hqCd",""),"slctnOrgGrdCd":"02","upOrgChngYn":None,"usInputObjcYn":None,"indcEmpNo":None,"indcNm":None})
def _cndtn(ltifm,pymn,mtrty,mtrtycf,ltiord,ltigen,cdc):
    return {"ltictCd":"03","ltifmCd":ltifm,"lngtrmContTdcd":"02","pymnPrdYrcnt":None,"pymnPrdYrcntCd":pymn,"pymnPrdCfcd":"1","insMtrtyYrcnt":None,"insMtrtyYrcntCd":mtrty,"insMtrtyCfcd":mtrtycf,"insPrdYrcnt":None,"pymnCyclCd":"L10","smplComprPrdtCfcd":"10","ltigenCd":ltigen,"ltifamCd":None,"ltiordCd":ltiord,"comprDesignCfcd":cdc}
def _obj(age="45",sex="1"):
    return {"objctSeq":"1","objtyCfcd":"L001","objctTpcd":"L00001","insdpsCncpsSeq":None,"sexCd":sex,"insAge":age,"fulage":age,"ocptCd":"B014","ocptCdNm":"전업주부","rateGrade":"1","riskGrdCd":"A","jobgrpGrade":"04","insdpsRlcd":"001","drivTdcd":"01","objtyInsBgdt":TODAY,"embrYn":"N","objctSttcd":"01","partyMncnt":"1","objGuarntPrem":0}
def _comn(w,a):
    return {"wrClsfc":w,"apcno":a,"apcDay":TODAY,"insBgdt":TODAY,"insEnddt":None,"apcSttcd":None if w=="I" else "00","apcJobKindCfcd":"01","saleChCfcd":"01","systemChfcd":"23","pdcd":PDCD,"prdtClcd":"202","inputScrenCfcd":"21","rncvrSptnApplYn":"Y"}
async def mkapc(cndtn,obj):
    r=await _call("LTI0100106",{"LtApcBasicInfoDTO":{"ltApcComnDTO":_comn("I",None),"ltApcTreatOrgDTO":dict(_treat_org),"ltApcPolhdInfoDTO":{},"ltApcObjDtlDTO":[obj],"ltApcContCndtnDTO":cndtn,"ltApcDcRateInfoDTO":[],"ltApcCvrInfoDTO":[dict(_NULL_CVR)],"ltApcPremDTO":{"acprm":None,"guarntPrem":0},"ltApcBnfcryDTO":{},"ltApcSettlBkacntDTO":{},"ltApcPyBkacntDTO":{},"ltApcInsdpsSuplmtInfoDTO":[],"ltApcContchngObjcDTO":[],"ltApcLoctInfoDTO":[],"ltApcPrprtGroupInfoDTO":[],"ltApcNtrPrprtCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcNtrPrprtEtcCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcPrprtRateFctrInfoDTO":[dict(_NULL_RATE_FCTR)],"ltApcCncpsDisblDeductInfoDTO":[dict(_NULL_DISBL)],"ltApcbfContInfoDTO":[],"ltApcCmpanmlInfoDTO":[],"etcMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"cvrMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"lngtrmAutoRvwPDTO":[dict(_NULL_AUTO_RVW)]}})
    return r.get("ErrorCode"), r.get("ErrorMsg"), r.get("ltApcBasicInfoOutDTO",{}).get("ltApcComnDTO",{}).get("apcno"), r.get("ltApcBasicInfoOutDTO",{}).get("ltApcContCndtnDTO",{})
def _mkbatch(sel):
    return [{"objctSeq":"1","objctTpcd":c.get("objctTpcd","L00001"),"cvrCd":c["cvrCd"],"cvrNm":c["cvrNm"],"cvrNtrSeq":c.get("cvrNtrSeq","1"),"cvrTpcd":c.get("cvrTpcd",""),"cvrNtrCkYn":"1","ntramtInputYn":c.get("ntramtInputYn","Y"),"pymnPrdInputYn":c.get("pymnPrdInputYn","N"),"insPrdInputYn":c.get("insPrdInputYn","N"),"cvrSuplmtButtonRvtztYn":"N","achngCvrPerpsNtramt":10_000_000,"achngCvrTnthwnUnitNtramt":1000,"cvrAchngCvrNtramt":10_000_000,"cvrFullNm":c.get("cvrFullNm",c["cvrNm"]),"ntrpsblCvrTpcd":c.get("ntrpsblCvrTpcd",""),"screnDispOrd":c.get("screnDispOrd","1")} for c in sel]
async def calc(apcno,cndtn,obj,sel):
    resp=await _call("LTI0103805",{"LngtrmApcRtimePremInqInfoDTO":{"rtimeCalYn":"Y","ltApcComnDTO":_comn("D",apcno),"ltApcContCndtnDTO":cndtn,"ltApcObjDtlDTO":obj,"ltApcCvrPremSuplmtInfoDTO":{},"ltApcCvrInfoDTO":_mkbatch(sel)}})
    items=resp.get("LTI0103805_O",{}).get("ltApcCvrInfoDTO",[])
    if not isinstance(items,list): items=[items]
    return {i.get("cvrCd"):i.get("achngCvrPrem") for i in items}
async def main():
    global _page
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); _page=await browser.new_page()
        await init_session(PDCD)
        r=await _call("LTI0100403",{"LngtrmNtrpsblCvrInqCndtnInfoDTO":{"pdcd":PDCD,"stdt":TODAY,"objctTpcd":"L00001"}})
        cvrs=r.get("LngtrmApcCvrInfoPDTO",{}).get("ltApcCvrInfoDTO",[])
        la=[c for c in cvrs if c.get("cvrCd","").startswith("LA")]
        lb=[c for c in cvrs if c.get("cvrCd","").startswith("LB")]
        la0=next(c for c in la if c["cvrCd"]=="LA0001")
        lb0=lb[0]
        obj=_obj()

        # 0) 서버 echo-back: 빈 apcno 만들고 서버가 채워준 cndtn 확인
        print("── 서버 echo-back cndtn (cdc=05,ltiord=00,ltigen=00,20납/100세) ──",flush=True)
        ec,em,apc,echoed=await mkapc(_cndtn("03","20","A0","2","00","00","05"),obj)
        keys=["comprDesignCfcd","ltiordCd","ltigenCd","smplComprPrdtCfcd","insMtrtyCfcd","insMtrtyYrcntCd","pymnPrdYrcntCd","ltifmCd","ltictCd","lngtrmContTdcd","pymnCyclCd"]
        print(f"   err={ec} echo={{ {', '.join(f'{k}:{echoed.get(k)!r}' for k in keys)} }}",flush=True)

        # 1) comprDesignCfcd 스윕 (LA0001, 20납/100세, ltiord/ltigen=00)
        print("\n── comprDesignCfcd 스윕 (LA0001, 20납/100세) ──",flush=True)
        for cdc in ["01","02","03","04","05","06","07","08","09","10"]:
            cndtn=_cndtn("03","20","A0","2","00","00",cdc)
            ec,em,apc,_=await mkapc(cndtn,obj)
            pr=(await calc(apc,cndtn,obj,[la0])).get("LA0001") if (str(ec)=="0" and apc) else f"apc({ec})"
            print(f"   cdc={cdc} → {pr}",flush=True)

        # 2) LB(갱신형) 특약을 24995식(연만기 10/10)으로 — 갱신특약은 따로 산출되나?
        print("\n── LB 갱신형 특약 (24995식 연만기 10/10, cdc=05/00/00) ──",flush=True)
        for ltifm,pymn,mtrty,mc in [("01","10","10","1"),("03","20","20","1"),("03","20","A0","2")]:
            cndtn=_cndtn(ltifm,pymn,mtrty,mc,"00","00","05")
            ec,em,apc,_=await mkapc(cndtn,obj)
            pr=(await calc(apc,cndtn,obj,[lb0])).get(lb0["cvrCd"]) if (str(ec)=="0" and apc) else f"apc({ec})"
            print(f"   {pymn}납/{mtrty}만기(cf{mc}) {lb0['cvrCd']} → {pr}",flush=True)
        await browser.close()
asyncio.run(main())
