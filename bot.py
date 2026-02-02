import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

# 깃허브 Secrets 설정값
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
USER_ID = os.environ.get('WM_ID')
USER_PW = os.environ.get('WM_PW')

async def main():
    # 주소 설정
    base_url = "https://www.thewm.co.kr"
    login_action_url = f"{base_url}/member/login_ok.asp"
    list_url = f"{base_url}/news/list.asp?np=News+Briefing&sid=S09"
    
    # 브라우저 위장용 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': f'{base_url}/member/login.asp',
        'Origin': base_url
    }

    # 로그인 전송 데이터
    login_data = {
        'user_id': USER_ID,
        'user_pwd': USER_PW,
        'login_chk': 'Y',
        're_url': '/main/main.asp' # 로그인 후 이동할 주소
    }

    try:
        # 1. 세션 생성 및 로그인 실행
        session = requests.Session()
        login_res = session.post(login_action_url, data=login_data, headers=headers)
        
        # 2. 뉴스 목록 페이지 접속
        res = session.get(list_url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # [핵심] 사진 속 볼드체 제목(News Briefing 섹션) 찾기
        # 링크 주소에 view.asp와 idx가 포함된 첫 번째 항목을 타겟팅
        first_post_link = None
        for a in soup.find_all('a', href=True):
            if 'view.asp' in a['href'] and 'idx=' in a['href']:
                if a.get_text(strip=True): # 텍스트가 있는 링크만 선택
                    first_post_link = a
                    break

        if not first_post_link:
            print("게시글 링크를 찾지 못했습니다. 로그인 상태를 점검하세요.")
            return

        post_url = base_url + "/news/" + first_post_link['href'].replace("./", "")
        print(f"접속 중: {post_url}")

        # 3. 본문 페이지 접속
        post_res = session.get(post_url, headers=headers)
        post_res.encoding = 'utf-8'
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        # 제목 및 본문 추출 (theWM 특정 클래스)
        title = post_soup.select_one('.view_title').get_text(strip=True) if post_soup.select_one('.view_title') else "제목 없음"
        content_div = post_soup.select_one('.view_content')
        
        if not content_div:
            content = "본문 권한이 없거나 내용을 읽을 수 없습니다."
        else:
            content = content_div.get_text("\n", strip=True)

        # 4. 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>📌 {title}</b>\n\n{content[:3800]}" # 텔레그램 제한 준수
        
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("🎉 텔레그램 전송 완료!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
