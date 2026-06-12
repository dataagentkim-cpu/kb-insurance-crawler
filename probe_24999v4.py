# 24999 확정 — 세만기 유효 납기/만기 + LA/LB prefix별 담보 커버리지 (batch=1, 재시도 포함)
import asyncio, json, sys, io
from datetime import date
from collections import Counter
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
def _cndtn(ltifm,pymn,mtrty,mtrtycf):
    return {"ltictCd":"03","ltifmCd":ltifm,"lngtrmContTdcd":"02","pymnPrdYrcnt":None,"pymnPrdYrcntCd":pymn,"pymnPrdCfcd":"1","insMtrtyYrcnt":None,"insMtrtyYrcntCd":mtrty,"insMtrtyCfcd":mtrtycf,"insPrdYrcnt":None,"pymnCyclCd":"L10","smplComprPrdtCfcd":"10","ltigenCd":"00","ltifamCd":None,"ltiordCd":"00","comprDesignCfcd":"05"}
def _obj(age="45",sex="1"):
    return {"objctSeq":"1","objtyCfcd":"L001","objctTpcd":"L00001","insdpsCncpsSeq":None,"sexCd":sex,"insAge":age,"fulage":age,"ocptCd":"B014","ocptCdNm":"전업주부","rateGrade":"1","riskGrdCd":"A","jobgrpGrade":"04","insdpsRlcd":"001","drivTdcd":"01","objtyInsBgdt":TODAY,"embrYn":"N","objctSttcd":"01","partyMncnt":"1","objGuarntPrem":0}
def _comn(w,a):
    return {"wrClsfc":w,"apcno":a,"apcDay":TODAY,"insBgdt":TODAY,"insEnddt":None,"apcSttcd":None if w=="I" else "00","apcJobKindCfcd":"01","saleChCfcd":"01","systemChfcd":"23","pdcd":PDCD,"prdtClcd":"202","inputScrenCfcd":"21","rncvrSptnApplYn":"Y"}
async def mkapc(cndtn,obj):
    r=await _call("LTI0100106",{"LtApcBasicInfoDTO":{"ltApcComnDTO":_comn("I",None),"ltApcTreatOrgDTO":dict(_treat_org),"ltApcPolhdInfoDTO":{},"ltApcObjDtlDTO":[obj],"ltApcContCndtnDTO":cndtn,"ltApcDcRateInfoDTO":[],"ltApcCvrInfoDTO":[dict(_NULL_CVR)],"ltApcPremDTO":{"acprm":None,"guarntPrem":0},"ltApcBnfcryDTO":{},"ltApcSettlBkacntDTO":{},"ltApcPyBkacntDTO":{},"ltApcInsdpsSuplmtInfoDTO":[],"ltApcContchngObjcDTO":[],"ltApcLoctInfoDTO":[],"ltApcPrprtGroupInfoDTO":[],"ltApcNtrPrprtCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcNtrPrprtEtcCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcPrprtRateFctrInfoDTO":[dict(_NULL_RATE_FCTR)],"ltApcCncpsDisblDeductInfoDTO":[dict(_NULL_DISBL)],"ltApcbfContInfoDTO":[],"ltApcCmpanmlInfoDTO":[],"etcMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"cvrMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"lngtrmAutoRvwPDTO":[dict(_NULL_AUTO_RVW)]}})
    return r.get("ErrorCode"), r.get("ltApcBasicInfoOutDTO",{}).get("ltApcComnDTO",{}).get("apcno")
def _b(c):
    return {"objctSeq":"1","objctTpcd":c.get("objctTpcd","L00001"),"cvrCd":c["cvrCd"],"cvrNm":c["cvrNm"],"cvrNtrSeq":c.get("cvrNtrSeq","1"),"cvrTpcd":c.get("cvrTpcd",""),"cvrNtrCkYn":"1","ntramtInputYn":c.get("ntramtInputYn","Y"),"pymnPrdInputYn":c.get("pymnPrdInputYn","N"),"insPrdInputYn":c.get("insPrdInputYn","N"),"cvrSuplmtButtonRvtztYn":"N","achngCvrPerpsNtramt":10_000_000,"achngCvrTnthwnUnitNtramt":1000,"cvrAchngCvrNtramt":10_000_000,"cvrFullNm":c.get("cvrFullNm",c["cvrNm"]),"ntrpsblCvrTpcd":c.get("ntrpsblCvrTpcd",""),"screnDispOrd":c.get("screnDispOrd","1")}
async def calc1(apcno,cndtn,obj,c,retries=3):
    for _ in range(retries):
        resp=await _call("LTI0103805",{"LngtrmApcRtimePremInqInfoDTO":{"rtimeCalYn":"Y","ltApcComnDTO":_comn("D",apcno),"ltApcContCndtnDTO":cndtn,"ltApcObjDtlDTO":obj,"ltApcCvrPremSuplmtInfoDTO":{},"ltApcCvrInfoDTO":[_b(c)]}})
        items=resp.get("LTI0103805_O",{}).get("ltApcCvrInfoDTO",[])
        if not isinstance(items,list): items=[items]
        v=items[0].get("achngCvrPrem") if items else None
        if v not in (None,): return v
    return None
async def main():
    global _page
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); _page=await browser.new_page()
        await init_session(PDCD)
        r=await _call("LTI0100403",{"LngtrmNtrpsblCvrInqCndtnInfoDTO":{"pdcd":PDCD,"stdt":TODAY,"objctTpcd":"L00001"}})
        cvrs=r.get("LngtrmApcCvrInfoPDTO",{}).get("ltApcCvrInfoDTO",[])
        la0=next(c for c in cvrs if c["cvrCd"]=="LA0001")
        obj=_obj()
        # 세만기 유효 납기/만기 (LA0001 사망 기준, 재시도 포함해 transient null 배제)
        print("── 세만기(cf2) 납기/만기 [LA0001, 재시도3] ──",flush=True)
        valid=[]
        for ltifm,pymn,mtrty in [("01","10","90"),("01","10","95"),("01","10","A0"),("02","15","90"),("02","15","95"),("02","15","A0"),("03","20","90"),("03","20","95"),("03","20","A0"),("","25","90"),("","25","A0"),("04","30","90"),("04","30","95"),("04","30","A0")]:
            cndtn=_cndtn(ltifm,pymn,mtrty,"2"); ec,apc=await mkapc(cndtn,obj)
            pr=await calc1(apc,cndtn,obj,la0) if (str(ec)=="0" and apc) else None
            ok=pr not in (None,"0",0)
            if ok: valid.append((ltifm,pymn,mtrty))
            print(f"   {'✓' if ok else '✗'} ltifm={ltifm:>2} {pymn}납/{mtrty}만기 → {pr}",flush=True)
        # 연만기(cf1)도 혹시 — 24999가 세만기 전용인지 확인
        print("\n── 연만기(cf1) 확인 [LA0001] ──",flush=True)
        for ltifm,pymn,mtrty in [("01","10","10"),("03","20","20"),("04","30","30")]:
            cndtn=_cndtn(ltifm,pymn,mtrty,"1"); ec,apc=await mkapc(cndtn,obj)
            pr=await calc1(apc,cndtn,obj,la0) if (str(ec)=="0" and apc) else None
            print(f"   {pymn}납/{mtrty}만기 → {pr}",flush=True)
        # 전체 LA+LB 담보 커버리지 (batch=1, 유효 첫 세만기 period)
        if valid:
            ltifm,pymn,mtrty=valid[0]
            allcv=[c for c in cvrs if c.get("cvrCd","")[:2] in ("LA","LB")]
            print(f"\n── 전체 담보 (LA+LB {len(allcv)}개, batch=1 재시도, {pymn}납/{mtrty}만기, 45세남) ──",flush=True)
            cndtn=_cndtn(ltifm,pymn,mtrty,"2"); ec,apc=await mkapc(cndtn,obj)
            sem=asyncio.Semaphore(8)
            async def one(c):
                async with sem: return c["cvrCd"], await calc1(apc,cndtn,obj,c)
            res=await asyncio.gather(*[one(c) for c in allcv])
            nn={k:v for k,v in res if v not in (None,"0",0)}
            byp=Counter(k[:2] for k in nn)
            print(f"   보험료>0: {len(nn)}개 / {len(allcv)} (prefix별 {dict(byp)})",flush=True)
            print(f"   LA0001={nn.get('LA0001')} | 샘플 {dict(list(nn.items())[:6])}",flush=True)
        await browser.close()
asyncio.run(main())
