import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

# 깃허브 Secrets 설정
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
USER_ID = os.environ.get('WM_ID')
USER_PW = os.environ.get('WM_PW')

async def main():
    session = requests.Session()
    base_url = "https://www.thewm.co.kr"
    
    # 1. 로그인 필수 헤더 설정 (실제 브라우저와 동일하게)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': f'{base_url}/member/login.asp',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # 2. 로그인 처리 (theWM 실제 폼 데이터 형식)
    login_url = f"{base_url}/member/login_ok.asp"
    login_data = {
        'user_id': USER_ID,
        'user_pwd': USER_PW,
        'login_chk': 'Y',
        're_url': '/main/main.asp'
    }

    try:
        # 로그인 실행
        print(f"로그인 시도 중: {USER_ID}")
        login_res = session.post(login_url, data=login_data, headers=headers)
        
        # 3. 뉴스 목록 페이지 접속 (sid=S09: News Briefing)
        list_url = f"{base_url}/news/list.asp?np=News+Briefing&sid=S09"
        res = session.get(list_url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # [수정] 뉴스 링크 찾기 (가장 정확한 패턴)
        first_post_link = None
        for a in soup.find_all('a', href=True):
            if 'view.asp' in a['href'] and 'idx=' in a['href']:
                if a.get_text(strip=True): # 제목 텍스트가 있는 링크
                    first_post_link = a['href']
                    break

        if not first_post_link:
            print("❌ 게시글을 찾을 수 없습니다. (ID/비번이나 권한 확인 필요)")
            return

        post_url = base_url + "/news/" + first_post_link.replace("./", "")
        print(f"✅ 뉴스 발견: {post_url}")

        # 4. 본문 내용 가져오기
        post_res = session.get(post_url, headers=headers)
        post_res.encoding = 'utf-8'
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        title = post_soup.select_one('.view_title').get_text(strip=True) if post_soup.select_one('.view_title') else "새 브리핑 업데이트"
        content_el = post_soup.select_one('.view_content') or post_soup.select_one('.cont_view')
        
        if content_el:
            content = content_el.get_text("\n", strip=True)
        else:
            content = "본문을 읽어올 수 없습니다. (유료 회원 권한 만료 여부 확인 필요)"

        # 5. 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>[theWM 브리핑]</b>\n\n<b>📌 {title}</b>\n\n{content[:3800]}"
        
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("🚀 전송 성공!")

    except Exception as e:
        print(f"⚠️ 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
