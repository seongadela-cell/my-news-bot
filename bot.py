import os
import re
import html
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


BASE_URL = "https://www.thewm.co.kr"
LOGIN_URL = f"{BASE_URL}/member/login.asp"
LIST_URL = f"{BASE_URL}/news/list.asp?np=News+Briefing&sid=S09"


def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def send_telegram(token: str, chat_id: str, text: str) -> None:
    # Telegram: sendMessage API (라이브러리 없이 requests로)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
        timeout=30,
    )
    r.raise_for_status()


def normalize_ws(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def main() -> None:
    TELEGRAM_TOKEN = must_env("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = must_env("TELEGRAM_CHAT_ID")
    WM_ID = must_env("WM_ID")
    WM_PW = must_env("WM_PW")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # 1) 로그인 페이지 진입
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        # 2) 로그인 폼 입력 (여기 selector가 사이트와 다르면 수정 포인트)
        # 보통 name이 user_id / user_pwd 형태
        page.fill('input[name="user_id"], input#user_id', WM_ID)
        page.fill('input[name="user_pwd"], input[name="user_pw"], input#user_pwd, input#user_pw', WM_PW)

        # submit 버튼 클릭 (여러 형태 대응)
        # - input[type=submit]
        # - button[type=submit]
        # - a 태그로 처리하는 사이트도 있어서 여러 후보로 시도
        clicked = False
        for sel in [
            'input[type="submit"]',
            'button[type="submit"]',
            'button:has-text("로그인")',
            'input[value*="로그인"]',
            'a:has-text("로그인")',
        ]:
            try:
                if page.locator(sel).first.is_visible():
                    page.locator(sel).first.click()
                    clicked = True
                    break
            except Exception:
                pass
        if not clicked:
            # 그래도 submit이 안 잡히면 form submit 시도
            try:
                page.locator("form").first.evaluate("form => form.submit()")
            except Exception as e:
                raise RuntimeError("Could not submit login form. Check selectors.") from e

        # 로그인 이후 네트워크 안정화 대기
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            # networkidle이 안 오는 사이트도 있어서 domcontentloaded라도 OK
            page.wait_for_load_state("domcontentloaded", timeout=15000)

        # 3) 목록 페이지로 이동
        page.goto(LIST_URL, wait_until="domcontentloaded")

        # 4) 첫 게시글 링크 찾기
        # view.asp 링크 중 "제목 텍스트가 있는 것" 우선
        page.wait_for_timeout(800)  # 렌더링 약간 대기
        links = page.locator('a[href*="view.asp"]')
        count = links.count()
        if count == 0:
            # 로그인 실패/권한 없음/차단일 때 흔함
            # 페이지 일부를 텔레그램으로 보내서 디버깅도 가능하게 함
            snippet = page.content()[:2000]
            raise RuntimeError("No view.asp links found. Possibly login failed or blocked.\n" + snippet)

        first_href = None
        for i in range(min(count, 50)):
            a = links.nth(i)
            text = (a.inner_text() or "").strip()
            href = a.get_attribute("href") or ""
            if "view.asp" in href and text:
                first_href = href
                break

        if not first_href:
            first_href = links.first.get_attribute("href")

        if not first_href:
            raise RuntimeError("Could not extract first post link.")

        # 상대경로 -> 절대경로
        if first_href.startswith("./"):
            first_href = first_href[2:]
        if first_href.startswith("/"):
            post_url = BASE_URL + first_href
        elif first_href.startswith("http"):
            post_url = first_href
        else:
            # 예: view.asp?... 형태면 /news/ 붙는 경우가 많아서 둘 다 시도
            post_url = f"{BASE_URL}/news/{first_href}"

        # 5) 게시글 페이지 이동
        page.goto(post_url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass

        # 6) 제목/본문 추출 (selector 후보 여러 개)
        title = ""
        for sel in [".view_title", ".tit_view", "h1", "h2"]:
            loc = page.locator(sel).first
            try:
                if loc.is_visible():
                    title = (loc.inner_text() or "").strip()
                    if title:
                        break
            except Exception:
                continue
        if not title:
            title = "theWM 브리핑 업데이트"

        content = ""
        for sel in [".view_content", ".cont_view", ".view_cont", "#content", "article"]:
            loc = page.locator(sel).first
            try:
                if loc.is_visible():
                    content = (loc.inner_text() or "").strip()
                    if content and len(content) > 20:
                        break
            except Exception:
                continue

        if not content:
            content = "본문을 읽어오지 못했습니다. (권한/차단/셀렉터 확인 필요)"

        browser.close()

    # 7) 텔레그램 전송 (HTML 깨짐 방지 위해 escape)
    safe_title = html.escape(normalize_ws(title))
    safe_content = html.escape(normalize_ws(content))

    # Telegram 메시지 길이 제한(4096) 고려해서 자르기
    msg = f"<b>[theWM 브리핑]</b>\n\n<b>📌 {safe_title}</b>\n\n{safe_content}"
    if len(msg) > 3800:
        msg = msg[:3800] + "\n\n(이하 생략)"

    send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
    print("✅ Sent to Telegram")


if __name__ == "__main__":
    main()
