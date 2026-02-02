import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

# 깃허브 Secrets에서 안전하게 가져오기
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
USER_ID = os.environ.get('WM_ID')
USER_PW = os.environ.get('WM_PW')

async def main():
    # 주소 설정
    login_url = "https://www.thewm.co.kr/member/login_ok.asp"
    list_url = "https://www.thewm.co.kr/news/list.asp?np=News+Briefing&sid=S09"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': 'https://www.thewm.co.kr/member/login.asp'
    }

    # 로그인 데이터 (theWM 사이트의 실제 필드명 반영)
    login_data = {
        'user_id': USER_ID,
        'user_pwd': USER_PW,
        'login_chk': 'Y'
    }

    try:
        session = requests.Session()
        
        # 1. 로그인 시도
        print(f"로그인 시도 중... (ID: {USER_ID})")
        login_res = session.post(login_url, data=login_data, headers=headers)
        
        # 2. 목록 페이지 접속
        res = session.get(list_url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # 첫 번째 뉴스 링크 찾기 (view.asp 패턴)
        first_post = None
        for link in soup.find_all('a', href=True):
            if 'view.asp' in link['href'] and 'idx=' in link['href']:
                if len(link.get_text(strip=True)) > 5:
                    first_post = link
                    break

        if not first_post:
            print("게시글을 찾을 수 없습니다. 로그인 상태나 권한을 확인하세요.")
            return

        post_url = "https://www.thewm.co.kr/news/" + first_post['href'].replace("./", "")
        print(f"찾은 뉴스 주소: {post_url}")

        # 3. 본문 페이지 접속 (로그인 세션 유지됨)
        post_res = session.get(post_url, headers=headers)
        post_res.encoding = 'utf-8'
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        # 제목 및 본문 추출
        title_el = post_soup.select_one('.view_title') or post_soup.find('strong')
        content_el = post_soup.select_one('.view_content') or post_soup.select_one('.cont_view')
        
        title = title_el.get_text(strip=True) if title_el else "새 뉴스 알림"
        content = content_el.get_text("\n", strip=True) if content_el else "본문 내용을 읽어올 수 없습니다 (권한 부족)."

        # 4. 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>[브리핑] {title}</b>\n\n{content[:3500]}..."
        
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("전송 성공!")

    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
