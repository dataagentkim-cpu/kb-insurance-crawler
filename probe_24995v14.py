# 24995 LB(맞춤고지) — plan x ltiord x comprDesign x ltigen 광범위 스윕
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
def _cndtn(cdc,plan,ltiord,ltigen):
    return {"ltictCd":"03","ltifmCd":"01","lngtrmContTdcd":plan,"pymnPrdYrcnt":None,"pymnPrdYrcntCd":"10","pymnPrdCfcd":"1","insMtrtyYrcnt":None,"insMtrtyYrcntCd":"10","insMtrtyCfcd":"1","insPrdYrcnt":None,"pymnCyclCd":"L10","smplComprPrdtCfcd":"10","ltigenCd":ltigen,"ltifamCd":None,"ltiordCd":ltiord,"comprDesignCfcd":cdc}
def _obj():
    return {"objctSeq":"1","objtyCfcd":"L001","objctTpcd":"L00001","insdpsCncpsSeq":None,"sexCd":"1","insAge":"45","fulage":"45","ocptCd":"B014","ocptCdNm":"전업주부","rateGrade":"1","riskGrdCd":"A","jobgrpGrade":"04","insdpsRlcd":"001","drivTdcd":"01","objtyInsBgdt":TODAY,"embrYn":"N","objctSttcd":"01","partyMncnt":"1","objGuarntPrem":0}
def _comn(w,a):
    return {"wrClsfc":w,"apcno":a,"apcDay":TODAY,"insBgdt":TODAY,"insEnddt":None,"apcSttcd":None if w=="I" else "00","apcJobKindCfcd":"01","saleChCfcd":"01","systemChfcd":"23","pdcd":PDCD,"prdtClcd":"202","inputScrenCfcd":"21","rncvrSptnApplYn":"Y"}
async def mkapc(cndtn):
    r=await _call("LTI0100106",{"LtApcBasicInfoDTO":{"ltApcComnDTO":_comn("I",None),"ltApcTreatOrgDTO":dict(_treat_org),"ltApcPolhdInfoDTO":{},"ltApcObjDtlDTO":[_obj()],"ltApcContCndtnDTO":cndtn,"ltApcDcRateInfoDTO":[],"ltApcCvrInfoDTO":[dict(_NULL_CVR)],"ltApcPremDTO":{"acprm":None,"guarntPrem":0},"ltApcBnfcryDTO":{},"ltApcSettlBkacntDTO":{},"ltApcPyBkacntDTO":{},"ltApcInsdpsSuplmtInfoDTO":[],"ltApcContchngObjcDTO":[],"ltApcLoctInfoDTO":[],"ltApcPrprtGroupInfoDTO":[],"ltApcNtrPrprtCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcNtrPrprtEtcCvrDTO":[dict(_NULL_PRPRT_CVR)],"ltApcPrprtRateFctrInfoDTO":[dict(_NULL_RATE_FCTR)],"ltApcCncpsDisblDeductInfoDTO":[dict(_NULL_DISBL)],"ltApcbfContInfoDTO":[],"ltApcCmpanmlInfoDTO":[],"etcMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"cvrMaterLngtrmRvwVioltInfoDTO":[dict(_NULL_RVW)],"lngtrmAutoRvwPDTO":[dict(_NULL_AUTO_RVW)]}})
    return r.get("ErrorCode"), r.get("ErrorMsg"), r.get("ltApcBasicInfoOutDTO",{}).get("ltApcComnDTO",{}).get("apcno")
async def calc(apcno,cndtn,sel):
    batch=[{"objctSeq":"1","objctTpcd":c.get("objctTpcd","L00001"),"cvrCd":c["cvrCd"],"cvrNm":c["cvrNm"],"cvrNtrSeq":c.get("cvrNtrSeq","1"),"cvrTpcd":c.get("cvrTpcd",""),"cvrNtrCkYn":"1","ntramtInputYn":c.get("ntramtInputYn","Y"),"pymnPrdInputYn":c.get("pymnPrdInputYn","N"),"insPrdInputYn":c.get("insPrdInputYn","N"),"cvrSuplmtButtonRvtztYn":"N","achngCvrPerpsNtramt":10_000_000,"achngCvrTnthwnUnitNtramt":1000,"cvrAchngCvrNtramt":10_000_000,"cvrFullNm":c.get("cvrFullNm",c["cvrNm"]),"ntrpsblCvrTpcd":c.get("ntrpsblCvrTpcd",""),"screnDispOrd":c.get("screnDispOrd","1")} for c in sel]
    resp=await _call("LTI0103805",{"LngtrmApcRtimePremInqInfoDTO":{"rtimeCalYn":"Y","ltApcComnDTO":_comn("D",apcno),"ltApcContCndtnDTO":cndtn,"ltApcObjDtlDTO":_obj(),"ltApcCvrPremSuplmtInfoDTO":{},"ltApcCvrInfoDTO":batch}})
    items=resp.get("LTI0103805_O",{}).get("ltApcCvrInfoDTO",[])
    if not isinstance(items,list): items=[items]
    return resp.get("ErrorCode"),resp.get("ErrorMsg"),[i.get("achngCvrPrem") for i in items]
async def main():
    global _page
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True); _page=await browser.new_page()
        await init_session(PDCD)
        r=await _call("LTI0100403",{"LngtrmNtrpsblCvrInqCndtnInfoDTO":{"pdcd":PDCD,"stdt":TODAY,"objctTpcd":"L00001"}})
        cvrs=r.get("LngtrmApcCvrInfoPDTO",{}).get("ltApcCvrInfoDTO",[])
        sel=[c for c in cvrs if c.get("cvrCd","").startswith("LB")][:2]
        print(f"담보 {len(cvrs)}개, 테스트 {[c['cvrCd'] for c in sel]}\n",flush=True)
        plans=["01","02","11","03","12","21","31"]
        ltiords=["00","03","04","14","15","16","17"]
        cdcs=["05","01"]
        ltigens=["04","00"]
        found=[]
        for cdc in cdcs:
          for plan in plans:
            for ltiord in ltiords:
              for ltigen in ltigens:
                cndtn=_cndtn(cdc,plan,ltiord,ltigen)
                ec,em,apcno=await mkapc(cndtn)
                if str(ec)!="0" or not apcno:
                    continue  # 무효 조합은 조용히 스킵
                pec,pem,prems=await calc(apcno,cndtn,sel)
                nonnull=[x for x in prems if x not in (None,"0",0)]
                if nonnull:
                    msg=f"✅ cdc={cdc} plan={plan} ltiord={ltiord} ltigen={ltigen} → {prems}"
                    print(msg,flush=True); found.append(msg)
        print(f"\n=== 비-null 조합 {len(found)}개 ===",flush=True)
        if not found:
            print("LTI0103805 로는 어떤 조합도 보험료 계산 불가 — 저장(LTI0100101)/위저드 경로 필요",flush=True)
        await browser.close()
asyncio.run(main())
