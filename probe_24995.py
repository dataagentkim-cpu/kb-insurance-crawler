# KB 5.10.10 플러스(24995) 상품 구조 조사 스크립트
"""
실행:
  python3 probe_24995.py

목적:
  - CT01_0495M.xml 인터페이스로 접근 가능한지 확인
  - LTI0100403으로 담보 목록 조회
  - UI 드롭다운에서 납기/만기/심사/납입면제 코드 추출
  - 결과를 probe_24995_result.json에 저장
"""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

PDCDS = ["24995", "24999"]  # 5.10.10 플러스 남성/여성(또는 표준/미지급)
API_ORIG  = "https://ppa.kbinsure.co.kr"
API_QUERY = "envrflag=ws&region=PD&sysgb=GW&user_key=4265768632&apnm=APP_KI&svcnm=DEVON"
OUT = Path(__file__).parent

_prohead_tpl = {}
_syshead_tpl = {}
_page = None


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
        try {{ return JSON.parse(text); }} catch(e) {{ return {{_raw: text.slice(0,500)}}; }}
    }}
    """
    return await _page.evaluate(script) or {}


DUMP_DATASETS_JS = """
() => {
    const safe = (fn) => { try { return fn(); } catch(e) { return null; } };
    const dsToJson = (ds) => { try { return ds.getAllJSON(); } catch(e) { return null; } };
    return {
        // 납기 목록
        pymnPrdList:  safe(() => dsToJson(ds_pymnPrdCdList) || dsToJson(ds_pymnPrdList)),
        // 만기 목록
        insMtrtyList: safe(() => dsToJson(ds_insMtrtyCdList) || dsToJson(ds_insMtrtyList)),
        // 심사고지유형
        ltictCdList:  safe(() => dsToJson(ds_ltictCdList)),
        // 납입면제
        napimList:    safe(() => dsToJson(ds_smplComprPrdtCfcdList) || dsToJson(ds_napimList)),
        // 플랜
        planList:     safe(() => dsToJson(ds_planList) || dsToJson(ds_comprDesignCfcdList)),
        // 연만기/세만기 구분
        insMtrtyCfcdList: safe(() => dsToJson(ds_insMtrtyCfcdList)),
        // 상품 기본 정보
        comnDTO:      safe(() => dsToJson(ds_ltApcComnDTO)),
        contCndtn:    safe(() => dsToJson(ds_ltApcContCndtnDTO)),
        // 전체 데이터셋 이름
        allDs: safe(() => Object.keys(window).filter(k => k.startsWith('ds_'))),
    };
}
"""


async def probe_product(pdcd):
    global _prohead_tpl, _syshead_tpl, _page

    print(f"\n{'='*60}")
    print(f"▶ 상품코드 {pdcd} 조사 시작")

    captured = {}

    async def on_response(resp):
        try:
            if "LTI0102102" in resp.url and "PROHEAD" not in captured:
                body = await resp.json()
                ph = body.get("PROHEAD", {})
                if ph:
                    captured["PROHEAD"] = ph
                    captured["SYSHEAD"] = body.get("SYSHEAD", {})
        except Exception:
            pass

    _page.on("response", on_response)

    url = f"{API_ORIG}/ppa/index_ws.jsp?gb=l&wsdl=ct_ui::CT01_0495M.xml&key1={pdcd}"
    print(f"  URL: {url}")
    await _page.goto(url)
    await _page.wait_for_load_state("networkidle")
    await asyncio.sleep(3)

    if not captured.get("PROHEAD"):
        print(f"  ⚠ PROHEAD 캡처 실패 — CT01_0495M.xml 인터페이스 아닐 수 있음")
        # 스크린샷으로 현재 상태 확인
        await _page.screenshot(path=str(OUT / f"probe_{pdcd}.png"), full_page=True)
        print(f"  📸 probe_{pdcd}.png 저장")
        return {"pdcd": pdcd, "error": "PROHEAD 캡처 실패"}

    _prohead_tpl = captured["PROHEAD"]
    _prohead_tpl["pfmFnCd"] = "CT01_0495M"
    _syshead_tpl = captured["SYSHEAD"]
    print(f"  ✓ PROHEAD 캡처 성공 (userId={_prohead_tpl.get('pfmUserId')})")

    # UI 드롭다운 데이터셋 추출 (WebSquare iframe)
    datasets = {}
    for frame in _page.frames:
        if frame.url and "8500" in frame.url:
            print(f"  WebSquare iframe: {frame.url[:60]}")
            try:
                datasets = await frame.evaluate(DUMP_DATASETS_JS)
                print("  ✓ 데이터셋 덤프 성공")
            except Exception as e:
                print(f"  ⚠ 데이터셋 덤프 실패: {e}")
            break

    # LTI0100403: 담보 목록 조회
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    cvr_resp = await _call_api("LTI0100403", {
        "LngtrmNtrpsblCvrInqCndtnInfoDTO": {"pdcd": pdcd, "stdt": today, "objctTpcd": "L00001"}
    })
    cvr_items = cvr_resp.get("LngtrmApcCvrInfoPDTO", {}).get("ltApcCvrInfoDTO", [])
    if not isinstance(cvr_items, list):
        cvr_items = [cvr_items]
    print(f"  담보 목록: {len(cvr_items)}개")

    # 담보 코드 prefix 확인
    prefixes = {}
    for c in cvr_items:
        cd = c.get("cvrCd", "")
        nm = c.get("cvrNm", "")
        pfx = cd[:2] if len(cd) >= 2 else cd
        prefixes[pfx] = prefixes.get(pfx, 0) + 1
    print(f"  담보 prefix 분포: {prefixes}")

    return {
        "pdcd": pdcd,
        "datasets": datasets,
        "cvr_count": len(cvr_items),
        "cvr_prefixes": prefixes,
        "cvr_sample": cvr_items[:5],
        "prohead_userId": _prohead_tpl.get("pfmUserId"),
    }


async def main():
    global _page

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        _page = await browser.new_page()

        results = {}
        for pdcd in PDCDS:
            try:
                result = await probe_product(pdcd)
                results[pdcd] = result
            except Exception as e:
                print(f"  ✗ 오류: {e}")
                results[pdcd] = {"pdcd": pdcd, "error": str(e)}

        out_path = OUT / "probe_24995_result.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✅ 결과 저장: {out_path}")

        # 주요 정보 요약 출력
        for pdcd, r in results.items():
            print(f"\n[{pdcd}]")
            if "error" in r:
                print(f"  오류: {r['error']}")
                continue
            print(f"  담보 수: {r['cvr_count']}, prefix: {r['cvr_prefixes']}")
            ds = r.get("datasets", {})
            for k in ["pymnPrdList", "insMtrtyList", "ltictCdList", "napimList", "planList"]:
                v = ds.get(k)
                if v:
                    print(f"  {k}: {v[:3]}...")
                else:
                    print(f"  {k}: (없음)")

        await browser.close()


asyncio.run(main())
