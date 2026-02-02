import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

async def main():
    # 뉴스브리핑 목록 주소
    list_url = "https://www.thewm.co.kr/news/list.asp?np=News+Briefing&sid=S09"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(list_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [수정] 사진 구조에 맞게 제목(볼드체) 링크를 직접 찾음
        # 상세 페이지는 보통 view.asp?idx= 형태임
        first_post = None
        for link in soup.find_all('a', href=True):
            if 'view.asp' in link['href'] and 'idx=' in link['href']:
                # 텍스트가 있는 첫 번째 유효한 링크 선택
                if link.get_text(strip=True):
                    first_post = link
                    break
        
        if not first_post:
            print("게시글 링크를 찾을 수 없습니다. 사이트 구조가 변경되었는지 확인하세요.")
            return
        
        # 상대 경로를 절대 경로로 변환
        href = first_post['href'].replace("./", "")
        post_url = "https://www.thewm.co.kr/news/" + href
        print(f"찾은 뉴스 주소: {post_url}")

        # 본문 페이지 접속
        post_res = requests.get(post_url, headers=headers)
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        # 제목과 본문 추출 (theWM 사이트 전용 클래스 반영)
        title_el = post_soup.select_one('.view_title') or post_soup.select_one('strong')
        content_el = post_soup.select_one('.view_content') or post_soup.select_one('.cont_view')
        
        title = title_el.get_text(strip=True) if title_el else "새로운 브리핑"
        content = content_el.get_text("\n", strip=True) if content_el else "본문은 사이트에서 확인해 주세요."

        # 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        # 제목 강조와 본문 (글자수 제한 대응)
        message = f"<b>[브리핑 업데이트]</b>\n\n<b>📌 {title}</b>\n\n{content[:3800]}"
        
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("전송 성공!")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
