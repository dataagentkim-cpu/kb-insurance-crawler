# 24995 유효 납기/만기 셋 확정 + 전체 LB담보 보험료 커버리지 확인
import asyncio, json, sys, io
from datetime import date
from playwright.async_api import async_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API_ORIG="https://ppa.kbinsure.co.kr"
API_QUERY="envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON"
TODAY=date.today().strftime("%Y-%m-%d")
PDCD="24995"
_prohead_tpl={}; _syshead_tpl={}; _treat_org={}; _page=None
from probe_24995v6 import (_NULL_CVR,_NULL_PRPRT_CVR,_NULL_RATE_FCTR,_NULL_DISBL,_NULL_RVW,_NULL_AUTO_RVW)

def _mrj(fn,body):
    ph=dict(_prohead_tpl); ph["pfmFnName"]=fn; ph["pfmGlobalNo"]=ph["pfmTrDate"]=ph["pfmTrTime"]=""
    return json.dumps({"PROHEAD":ph,"SYSHEAD":dict(_syshead_tpl),**body},ensure_ascii=False)
async def _call(fn,body):
    url=f"{API_ORIG}/po-21/APP_EG/SG_EG/WS/v1/APP_KI/DEVON/{fn}?{API_QUERY}"
    rj=_mrj(fn,body)
    s=f"""async()=>{{const r=await fetch({json.dumps(url)},{{method:'POST',headers:{{'Content-Type':'application/json'}},body:{json.dumps(rj)}}});const t=await r.text();try{{return JSON.parse(t)}}catch(e){{return{{_raw:t.slice(0,400)}}}}}}"""
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

def _cndtn(ltifm,pymn,mtrty,mtrtycf):
    return {"ltictCd":"03","ltifmCd":ltifm,"lngtrmContTdcd":"02","pymnPrdYrcnt":None,"pymnPrdYrcntCd":pymn,"pymnPrdCfcd":"1","insMtrtyYrcnt":None,"insMtrtyYrcntCd":mtrty,"insMtrtyCfcd":mtrtycf,"insPrdYrcnt":None,"pymnCyclCd":"L10","smplComprPrdtCfcd":"10","ltigenCd":"00","ltifamCd":None,"ltiordCd":"00","comprDesignCfcd":"05"}
def _obj(age="45",sex="1"):
    return {"objctSeq":"1","objtyCfcd":"L001","objctTpcd":"L00001","insdpsCncpsSeq":None,"sexCd":sex,"insAge":age,"fulage":age,"ocptCd":"B014","ocptCdNm":"전업주부","rateGrade":"1","riskGrdCd":"A","jobgrpGrade":"04","insdpsRlcd":"001","drivTdcd":"01","objtyInsBgdt":TODAY,"embrYn":"N","objctSttcd":"01","partyMncnt":"1","objGuarntPrem":0}
def _comn(w,a):
    return {"wrClsfc":w,"apcno":a,"apcDay":TODAY,"insBgdt":TODAY,"insEnddt":None,"apcSttcd":None if w=="I" else "00","apcJobKindCfcd":"01","saleChCfcd":"01","systemChfcd":"23","pdcd":PDCD,"prdtClcd":"202","inputScrenCfcd":"21","rncvrSptnApplYn":"Y"}
async def mkapc(cndtn,obj):
    r=await _call("LTI0100106",{"LtApcBasicInfoDTO":{"ltApcComnDTO":_comn("I",None),"ltApcTreatOrgDTO":dict(_treat_org),"ltApcPolhdInfoDTO":{},"ltApcObjDtlDTO":[obj],"ltApcContCndtnDTO":cndtn,"ltApcDcRateInfoDTO":[],"ltApcCvrInfoDTO":[dict(_NULL_CVR)],"ltApcPremDTO":{"acprm":None,"guarntPrem":0},"ltApcBnfcryDTO":{},"ltApcSettlBkacntDTO":{},"ltApcPyBkacntDTO":{},"ltApcInsdpsSuplmtInfoDTO":[],"ltApcContchngObjcDTO":[],"ltApcLoctInfoDTO":[],"ltApcPrprtGroupInfoDTO":[],"ltApcNtrPrprtCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcNtrPrprtEtcCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcPrprtRateFctrInfoDTO":[dict(_NULL_RATE_FCTR)],"ltApcCncpsDisblDeductInfoDTO":[dict(_NULL_DISBL)],"ltApcbfContInfoDTO":[],"ltApcCmpanmlInfoDTO":[],"etcMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"cvrMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"lngtrmAutoRvwPDTO":[dict(_NULL_AUTO_RVW)]}})
    return r.get("ErrorCode"), r.get("ltApcBasicInfoOutDTO",{}).get("ltApcComnDTO",{}).get("apcno")
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
        lb=[c for c in cvrs if c.get("cvrCd","").startswith("LB")]
        print(f"LB담보 {len(lb)}개\n",flush=True)
        obj=_obj()
        cvr0=next(c for c in lb if c["cvrCd"]=="LB0174")

        # 1) 납기/만기 유효셋 — 연만기갱신형(mtrtycf=1) 납기=만기 + 교차
        print("── 연만기갱신형(insMtrtyCfcd=1) 납기/만기 ──",flush=True)
        period_cands=[("01","05","05"),("01","10","10"),("02","15","15"),("03","20","20"),
                      ("04","30","30"),("01","10","20"),("01","10","30"),("","20","30"),("","25","25")]
        valid_periods=[]
        for ltifm,pymn,mtrty in period_cands:
            cndtn=_cndtn(ltifm,pymn,mtrty,"1")
            ec,apcno=await mkapc(cndtn,obj)
            pr=None
            if str(ec)=="0" and apcno:
                pr=(await calc(apcno,cndtn,obj,[cvr0])).get("LB0174")
            mark="✓" if pr not in (None,"0",0) else "✗"
            if pr not in (None,"0",0): valid_periods.append((ltifm,pymn,mtrty))
            print(f"   {mark} ltifm={ltifm:>2} {pymn}납/{mtrty}만기 → {pr}",flush=True)

        # 세만기 변형도 잠깐 확인(mtrtycf=2, 90/95/100세)
        print("\n── 세만기(insMtrtyCfcd=2) 확인 ──",flush=True)
        for ltifm,pymn,mtrty in [("01","10","90"),("03","20","A0"),("04","30","A0")]:
            cndtn=_cndtn(ltifm,pymn,mtrty,"2")
            ec,apcno=await mkapc(cndtn,obj)
            pr=None
            if str(ec)=="0" and apcno:
                pr=(await calc(apcno,cndtn,obj,[cvr0])).get("LB0174")
            print(f"   ltifm={ltifm:>2} {pymn}납/{mtrty}세 → {pr}",flush=True)

        # 2) 전체 LB담보 보험료 커버리지 (유효 첫 period 사용, 20개씩 배치)
        if valid_periods:
            ltifm,pymn,mtrty=valid_periods[0]
            print(f"\n── 전체 LB담보 보험료 (period={pymn}납/{mtrty}만기, 45세남) ──",flush=True)
            cndtn=_cndtn(ltifm,pymn,mtrty,"1")
            ec,apcno=await mkapc(cndtn,obj)
            allp={}
            for i in range(0,len(lb),20):
                allp.update(await calc(apcno,cndtn,obj,lb[i:i+20]))
            nonnull={k:v for k,v in allp.items() if v not in (None,"0",0)}
            print(f"   전체 {len(lb)}개 중 보험료>0: {len(nonnull)}개",flush=True)
            print(f"   샘플: {dict(list(nonnull.items())[:8])}",flush=True)
        await browser.close()
asyncio.run(main())
