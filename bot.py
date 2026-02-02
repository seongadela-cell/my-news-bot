import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

async def main():
    # 뉴스 목록 주소 (News Briefing 전용)
    list_url = "https://www.thewm.co.kr/news/list.asp?np=News+Briefing&sid=S09"
    
    # 실제 브라우저처럼 보이기 위한 강력한 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.thewm.co.kr/',
        'Connection': 'keep-alive'
    }
    
    try:
        # 세션을 사용하여 연결 유지
        session = requests.Session()
        res = session.get(list_url, headers=headers, timeout=20)
        res.encoding = 'utf-8' 
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [정밀 타격] 'view.asp?idx='가 포함된 모든 링크를 찾음
        all_links = soup.find_all('a', href=True)
        target_href = None
        
        for link in all_links:
            href = link['href']
            # 뉴스 상세 페이지 패턴 확인
            if 'view.asp' in href and 'idx=' in href:
                # 텍스트가 존재하고 5자 이상인 첫 번째 링크(제목)를 선택
                if len(link.get_text(strip=True)) > 5:
                    target_href = href
                    break
        
        if not target_href:
            print("게시글을 찾을 수 없습니다. 사이트 구조가 평소와 다릅니다.")
            return
        
        # 주소 조합 (상대 경로 제거)
        clean_href = target_href.replace("./", "")
        post_url = f"https://www.thewm.co.kr/news/{clean_href}"
        print(f"찾은 뉴스 주소: {post_url}")

        # 본문 페이지 접속
        post_res = session.get(post_url, headers=headers, timeout=20)
        post_res.encoding = 'utf-8'
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        # 제목 및 본문 추출 (theWM 전용 구조)
        title_el = post_soup.select_one('.view_title') or post_soup.find('strong')
        content_el = post_soup.select_one('.view_content') or post_soup.select_one('.cont_view')
        
        title = title_el.get_text(strip=True) if title_el else "뉴스 브리핑"
        content = content_el.get_text("\n", strip=True) if content_el else "본문 내용은 원문을 확인해 주세요."

        # 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>[브리핑 알림]</b>\n\n<b>📌 {title}</b>\n\n{content[:3000]}...\n\n🔗 <a href='{post_url}'>원문 보기</a>"
        
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("전송 성공!")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
