import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

async def main():
    # 뉴스브리핑 목록 주소 (sid=S09)
    list_url = "https://www.thewm.co.kr/news/list.asp?np=News+Briefing&sid=S09"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(list_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [수정] 모든 <a> 태그 중 주소에 'view.asp'가 포함된 첫 번째 링크를 찾음
        first_post = soup.find('a', href=lambda x: x and 'view.asp' in x)
        
        if not first_post:
            print("게시글 링크를 찾을 수 없습니다. 사이트 구조를 다시 확인해야 합니다.")
            return
        
        post_url = "https://www.thewm.co.kr/news/" + first_post['href']
        print(f"찾은 뉴스 주소: {post_url}")

        # 본문 페이지 접속
        post_res = requests.get(post_url, headers=headers)
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        # 제목과 본문 추출 (클래스명이 다를 경우를 대비해 안전하게 추출)
        title_el = post_soup.select_one('.view_title')
        content_el = post_soup.select_one('.view_content')
        
        title = title_el.get_text(strip=True) if title_el else "제목 없음"
        content = content_el.get_text("\n", strip=True) if content_el else "본문 내용을 가져올 수 없습니다."

        # 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>[브리핑 업데이트]</b>\n\n<b>제목: {title}</b>\n\n{content[:3000]}..."
        
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("전송 성공!")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
