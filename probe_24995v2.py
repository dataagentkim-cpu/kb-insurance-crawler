# KB 5.10.10 플러스(24995/24999) 코드값 캡처 스크립트 v2
"""
페이지 로드 시 발생하는 모든 API 응답을 캡처해서
납기/만기/심사/납입면제/comprDesignCfcd 코드값 추출
"""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

API_ORIG = "https://ppa.kbinsure.co.kr"
OUT = Path(__file__).parent

KEYWORDS = [
    "ltifm", "pymnPrd", "insMtrty", "ltict", "smplComprPrdt",
    "comprDesign", "napim", "ltiord", "ltigen", "lngtrmContTd",
    "pdcrtItm", "CdList", "cdList", "codeList", "selectList",
    "ltApcContCndtn", "ltApcComn",
]


async def capture_product(pdcd: str, browser):
    page = await browser.new_page()
    captured_responses = []
    form_selects = {}

    async def on_response(resp):
        try:
            if resp.request.resource_type not in ("xhr", "fetch"):
                return
            url = resp.url
            if not ("kbinsure" in url):
                return
            body = await resp.json()
            body_str = json.dumps(body, ensure_ascii=False)
            if any(kw.lower() in body_str.lower() for kw in KEYWORDS):
                captured_responses.append({"url": url, "body": body})
        except Exception:
            pass

    page.on("response", on_response)

    url = f"{API_ORIG}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1={pdcd}"
    print(f"\n[{pdcd}] 로딩: {url}")
    await page.goto(url)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(4)

    # iframe에서 select 요소 읽기
    for frame in page.frames:
        if not frame.url or "kbinsure" not in frame.url:
            continue
        try:
            selects = await frame.evaluate("""
            () => {
                const result = {};
                document.querySelectorAll('select').forEach(sel => {
                    const id = sel.id || sel.name || '?';
                    result[id] = [...sel.options].map(o => ({v: o.value, t: o.text.trim()}));
                });
                // WebSquare 컴포넌트 직접 탐색
                const wqSels = {};
                if (window.w2) {
                    try {
                        const ids = Object.keys(window.w2._components || {});
                        ids.forEach(id => {
                            const c = window.w2._components[id];
                            if (c && c.getDataList) {
                                try { wqSels[id] = c.getDataList(); } catch(e) {}
                            }
                        });
                    } catch(e) {}
                }
                return {selects: result, wqSelects: wqSels};
            }
            """)
            if selects.get("selects") or selects.get("wqSelects"):
                form_selects[frame.url[:80]] = selects
        except Exception as e:
            pass

    # 모든 iframe window 변수 확인
    for frame in page.frames:
        if not frame.url or "kbinsure" not in frame.url:
            continue
        try:
            vars_info = await frame.evaluate("""
            () => {
                const result = {};
                // ds_ 로 시작하는 모든 변수
                const dsKeys = Object.getOwnPropertyNames(window).filter(k => k.startsWith('ds_'));
                dsKeys.forEach(k => {
                    try {
                        const ds = window[k];
                        if (ds && typeof ds.getAllJSON === 'function') {
                            const data = ds.getAllJSON();
                            if (data && data.length > 0) result[k] = data.slice(0, 10);
                        } else if (ds && typeof ds.length !== 'undefined') {
                            result[k] = `length=${ds.length}`;
                        }
                    } catch(e) { result[k] = `err: ${e.message}`; }
                });
                // gf_ 로 시작하는 폼 변수
                const gfKeys = Object.getOwnPropertyNames(window).filter(k => k.startsWith('gf_'));
                gfKeys.slice(0, 20).forEach(k => {
                    try { result[k] = window[k]; } catch(e) {}
                });
                return result;
            }
            """)
            if vars_info:
                form_selects[f"vars_{frame.url[:40]}"] = vars_info
        except Exception:
            pass

    await page.close()

    result = {
        "pdcd": pdcd,
        "api_responses": captured_responses,
        "form_data": form_selects,
    }
    return result


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        all_results = {}

        for pdcd in ["24995", "24999"]:
            r = await capture_product(pdcd, browser)
            all_results[pdcd] = r

            print(f"\n[{pdcd}] API 응답 {len(r['api_responses'])}개 캡처")
            for resp in r["api_responses"][:5]:
                url_short = resp["url"].split("/")[-1].split("?")[0]
                print(f"  {url_short}")

            print(f"[{pdcd}] form_data 키: {list(r['form_data'].keys())[:5]}")

        out = OUT / "probe_24995v2_result.json"
        out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 저장: {out}")
        await browser.close()


asyncio.run(main())
