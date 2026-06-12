# 24995 보험료 변동 축 식별 — 한 담보(LB0001) 고정, 차원별 1개씩 변화
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

BASE=dict(cdc="05",plan="02",ltiord="00",ltigen="00",ltifm="01",pymn="10",mtrty="10",mtrtycf="1",
          sex="1",age="45",ocpt="B014",rg="1",rc="A",jg="04",driv="01")
def _cndtn(d):
    return {"ltictCd":"03","ltifmCd":d["ltifm"],"lngtrmContTdcd":d["plan"],"pymnPrdYrcnt":None,"pymnPrdYrcntCd":d["pymn"],"pymnPrdCfcd":"1","insMtrtyYrcnt":None,"insMtrtyYrcntCd":d["mtrty"],"insMtrtyCfcd":d["mtrtycf"],"insPrdYrcnt":None,"pymnCyclCd":"L10","smplComprPrdtCfcd":"10","ltigenCd":d["ltigen"],"ltifamCd":None,"ltiordCd":d["ltiord"],"comprDesignCfcd":d["cdc"]}
def _obj(d):
    return {"objctSeq":"1","objtyCfcd":"L001","objctTpcd":"L00001","insdpsCncpsSeq":None,"sexCd":d["sex"],"insAge":d["age"],"fulage":d["age"],"ocptCd":d["ocpt"],"ocptCdNm":"전업주부","rateGrade":d["rg"],"riskGrdCd":d["rc"],"jobgrpGrade":d["jg"],"insdpsRlcd":"001","drivTdcd":d["driv"],"objtyInsBgdt":TODAY,"embrYn":"N","objctSttcd":"01","partyMncnt":"1","objGuarntPrem":0}
def _comn(w,a):
    return {"wrClsfc":w,"apcno":a,"apcDay":TODAY,"insBgdt":TODAY,"insEnddt":None,"apcSttcd":None if w=="I" else "00","apcJobKindCfcd":"01","saleChCfcd":"01","systemChfcd":"23","pdcd":PDCD,"prdtClcd":"202","inputScrenCfcd":"21","rncvrSptnApplYn":"Y"}
async def mkapc(d):
    cndtn=_cndtn(d)
    r=await _call("LTI0100106",{"LtApcBasicInfoDTO":{"ltApcComnDTO":_comn("I",None),"ltApcTreatOrgDTO":dict(_treat_org),"ltApcPolhdInfoDTO":{},"ltApcObjDtlDTO":[_obj(d)],"ltApcContCndtnDTO":cndtn,"ltApcDcRateInfoDTO":[],"ltApcCvrInfoDTO":[dict(_NULL_CVR)],"ltApcPremDTO":{"acprm":None,"guarntPrem":0},"ltApcBnfcryDTO":{},"ltApcSettlBkacntDTO":{},"ltApcPyBkacntDTO":{},"ltApcInsdpsSuplmtInfoDTO":[],"ltApcContchngObjcDTO":[],"ltApcLoctInfoDTO":[],"ltApcPrprtGroupInfoDTO":[],"ltApcNtrPrprtCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcNtrPrprtEtcCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcPrprtRateFctrInfoDTO":[dict(_NULL_RATE_FCTR)],"ltApcCncpsDisblDeductInfoDTO":[dict(_NULL_DISBL)],"ltApcbfContInfoDTO":[],"ltApcCmpanmlInfoDTO":[],"etcMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"cvrMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"lngtrmAutoRvwPDTO":[dict(_NULL_AUTO_RVW)]}})
    return r.get("ErrorCode"), r.get("ltApcBasicInfoOutDTO",{}).get("ltApcComnDTO",{}).get("apcno")
async def prem(d, cvr):
    ec,apcno=await mkapc(d)
    if str(ec)!="0" or not apcno: return None
    batch=[{"objctSeq":"1","objctTpcd":cvr.get("objctTpcd","L00001"),"cvrCd":cvr["cvrCd"],"cvrNm":cvr["cvrNm"],"cvrNtrSeq":cvr.get("cvrNtrSeq","1"),"cvrTpcd":cvr.get("cvrTpcd",""),"cvrNtrCkYn":"1","ntramtInputYn":cvr.get("ntramtInputYn","Y"),"pymnPrdInputYn":cvr.get("pymnPrdInputYn","N"),"insPrdInputYn":cvr.get("insPrdInputYn","N"),"cvrSuplmtButtonRvtztYn":"N","achngCvrPerpsNtramt":10_000_000,"achngCvrTnthwnUnitNtramt":1000,"cvrAchngCvrNtramt":10_000_000,"cvrFullNm":cvr.get("cvrFullNm",cvr["cvrNm"]),"ntrpsblCvrTpcd":cvr.get("ntrpsblCvrTpcd",""),"screnDispOrd":cvr.get("screnDispOrd","1")}]
    resp=await _call("LTI0103805",{"LngtrmApcRtimePremInqInfoDTO":{"rtimeCalYn":"Y","ltApcComnDTO":_comn("D",apcno),"ltApcContCndtnDTO":_cndtn(d),"ltApcObjDtlDTO":_obj(d),"ltApcCvrPremSuplmtInfoDTO":{},"ltApcCvrInfoDTO":batch}})
    items=resp.get("LTI0103805_O",{}).get("ltApcCvrInfoDTO",[])
    if not isinstance(items,list): items=[items]
    return items[0].get("achngCvrPrem") if items else None
async def main():
    global _page
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); _page=await browser.new_page()
        await init_session(PDCD)
        r=await _call("LTI0100403",{"LngtrmNtrpsblCvrInqCndtnInfoDTO":{"pdcd":PDCD,"stdt":TODAY,"objctTpcd":"L00001"}})
        cvrs=r.get("LngtrmApcCvrInfoPDTO",{}).get("ltApcCvrInfoDTO",[])
        cvr=next(c for c in cvrs if c["cvrCd"]=="LB0174")  # 후유장해 — 금액따라 변동
        print(f"기준담보 {cvr['cvrCd']} {cvr['cvrNm'][:30]}\n",flush=True)
        async def sweep(label, key, vals):
            print(f"── {label} ({key}) ──",flush=True)
            for v in vals:
                d=dict(BASE); d[key]=v
                pr=await prem(d,cvr)
                print(f"   {key}={v:>4} → {pr}",flush=True)
            print(flush=True)
        await sweep("납입면제","ltigen",["00","04","11","14","01","02","10"])
        await sweep("심사차수","ltiord",["00","03","04","14","15","16","17"])
        await sweep("플랜","plan",["01","02","11"])
        await sweep("설계방식","cdc",["05","01","04"])
        await sweep("성별","sex",["1","2"])
        await sweep("나이","age",["30","45","60"])
        # 납기/만기 (연만기갱신형: insMtrtyCfcd=1)
        print("── 납기/만기 (ltifm,pymn,mtrty) ──",flush=True)
        for ltifm,pymn,mtrty in [("01","10","10"),("02","15","15"),("03","20","20"),("04","30","30"),("01","10","20")]:
            d=dict(BASE); d["ltifm"],d["pymn"],d["mtrty"]=ltifm,pymn,mtrty
            pr=await prem(d,cvr)
            print(f"   {pymn}납/{mtrty}만기 → {pr}",flush=True)
        await browser.close()
asyncio.run(main())
