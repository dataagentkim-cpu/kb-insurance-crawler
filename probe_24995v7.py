# KB 5.10.10 플러스 UI 클릭 후 LTI0103805 실제 요청 캡처
"""
headless 모드에서 24995 페이지 로드 후 보험료 산출 버튼 클릭 시도
LTI0103805 요청/응답 body 전체 캡처
"""
import asyncio, json
from playwright.async_api import async_playwright

API_ORIG = "https://ppa.kbinsure.co.kr"

async def main():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    req_log = {}
    resp_log = {}

    async def on_req(req):
        if "/APP_KI/DEVON/" in req.url:
            fn = req.url.split("/APP_KI/DEVON/")[1].split("?")[0]
            try:
                body = json.loads(req.post_data or "{}")
                req_log.setdefault(fn, []).append(body)
            except:
                pass

    async def on_resp(resp):
        if "/APP_KI/DEVON/" in resp.url:
            fn = resp.url.split("/APP_KI/DEVON/")[1].split("?")[0]
            try:
                body = await resp.json()
                resp_log.setdefault(fn, []).append(body)
            except:
                pass

    page.on("request", on_req)
    page.on("response", on_resp)

    print("▶ 24995 페이지 로드...")
    await page.goto(f"{API_ORIG}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1=24995")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(4)

    print(f"  초기 API 함수: {list(req_log.keys())}")

    # 모든 iframe 확인
    print(f"\n  Frames ({len(page.frames)}개):")
    for i, f in enumerate(page.frames):
        print(f"    [{i}] {f.url[:80]}")

    # WebSquare iframe에서 버튼/인풋 요소 탐색
    prem_btn_found = False
    for frame in page.frames:
        if not frame.url or "kbinsure" not in frame.url:
            continue
        try:
            ui = await frame.evaluate("""
            () => {
                const buttons = [...document.querySelectorAll('button, input[type=button], input[type=submit], a')].map(el => ({
                    tag: el.tagName, id: el.id, text: (el.textContent || el.value || '').trim().slice(0, 30),
                    onclick: el.getAttribute('onclick'), href: el.href
                })).filter(el => el.text || el.onclick);

                const inputs = [...document.querySelectorAll('input, select')].slice(0, 20).map(el => ({
                    type: el.type, id: el.id, name: el.name, value: el.value
                }));

                return {url: location.href, buttons: buttons.slice(0, 30), inputs};
            }
            """)
            if ui.get("buttons") or ui.get("inputs"):
                print(f"\n  Frame [{frame.url[:60]}]:")
                print(f"    버튼 {len(ui.get('buttons',[]))}개: {[b['text'] for b in ui.get('buttons',[])[:10]]}")
                print(f"    입력 {len(ui.get('inputs',[]))}개")
                prem_btn_found = True
        except Exception as e:
            pass

    if not prem_btn_found:
        print("  → UI 요소 없음, WebSquare 컴포넌트 직접 접근 시도")

    # 보험료 산출 버튼 직접 클릭 시도
    for frame in page.frames:
        if not frame.url or "kbinsure" not in frame.url:
            continue
        try:
            # 보험료 산출 관련 버튼 클릭
            result = await frame.evaluate("""
            () => {
                // WebSquare 컴포넌트 호출 시도
                const fns = ['fn_calPrem', 'fn_premCal', 'fn_calc', 'calPrem', 'premCal',
                             'fn_searchPrem', 'calcPrem', 'goCalcPrem', 'btnPremCal'];
                const found = fns.filter(f => typeof window[f] === 'function');
                if (found.length > 0) {
                    try { window[found[0]](); return `called: ${found[0]}`; } catch(e) { return `err: ${e.message}`; }
                }
                // 버튼 텍스트로 찾기
                const btns = [...document.querySelectorAll('button, input[type=button]')];
                const premBtn = btns.find(b => (b.textContent || b.value || '').includes('보험료'));
                if (premBtn) { premBtn.click(); return `clicked: ${premBtn.textContent || premBtn.value}`; }
                return `no button found. fns: ${Object.keys(window).filter(k => k.includes('prem') || k.includes('Prem') || k.includes('calc')).slice(0,10)}`;
            }
            """)
            print(f"\n  클릭 시도: {result}")
            if result and "no button" not in result:
                break
        except Exception as e:
            pass

    await asyncio.sleep(3)

    # LTI0103805 캡처 여부 확인
    print(f"\n  클릭 후 API 함수: {list(req_log.keys())}")

    if "LTI0103805" in req_log:
        body = req_log["LTI0103805"][0]
        # PROHEAD/SYSHEAD 제외하고 핵심 파라미터만 출력
        dto = body.get("LngtrmApcRtimePremInqInfoDTO", {})
        cndtn = dto.get("ltApcContCndtnDTO", {})
        comn  = dto.get("ltApcComnDTO", {})
        print("\n  LTI0103805 요청 cndtn:")
        print(json.dumps(cndtn, ensure_ascii=False, indent=2))
        print("\n  LTI0103805 요청 comn (핵심):")
        important = {k: v for k, v in comn.items() if v and k in ['wrClsfc','pdcd','prdtClcd','apcno','apcSttcd']}
        print(json.dumps(important, ensure_ascii=False, indent=2))

        # 응답에서 보험료 확인
        if "LTI0103805" in resp_log:
            r = resp_log["LTI0103805"][0]
            items = r.get("LTI0103805_O", {}).get("ltApcCvrInfoDTO", [])
            nonzero = [i for i in items if i.get("achngCvrPrem") and int(i.get("achngCvrPrem")) > 0]
            print(f"\n  보험료>0 담보: {len(nonzero)}개")
            for item in nonzero[:3]:
                print(f"    {item['cvrCd']} {item['cvrNm'][:30]}: {item['achngCvrPrem']}원")
    else:
        print("  LTI0103805 캡처 안됨 — 다른 방식 필요")

        # LTI0100106 요청 분석
        if "LTI0100106" in req_log:
            body = req_log["LTI0100106"][0]
            dto = body.get("LtApcBasicInfoDTO", {})
            cndtn = dto.get("ltApcContCndtnDTO", {})
            print("\n  LTI0100106 cndtn (초기화 시 자동 호출):")
            print(json.dumps(cndtn, ensure_ascii=False, indent=2))

    await browser.close()


asyncio.run(main())
