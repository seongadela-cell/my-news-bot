import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

async def main():
    # 네가 준 뉴스브리핑 전용 주소 (sid=S09)
    list_url = "https://www.thewm.co.kr/news/list.asp?np=News+Briefing&sid=S09"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(list_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 목록에서 첫 번째 게시글 찾기
        first_post = soup.select_one('table.board_list tbody tr a')
        if not first_post:
            print("게시글을 찾을 수 없습니다.")
            return
        
        post_url = "https://www.thewm.co.kr/news/" + first_post['href']

        # 중복 체크
        last_link_file = "last_link.txt"
        if os.path.exists(last_link_file):
            with open(last_link_file, "r") as f:
               # if f.read().strip() == post_url:
                   # print("새로운 글이 없습니다.")
                   # return

        # 본문 페이지 접속 및 추출
        post_res = requests.get(post_url, headers=headers)
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        
        title = post_soup.select_one('.view_title').get_text(strip=True)
        # 본문 내용 전체 (광고나 불필요한 태그 제외하고 텍스트만)
        content = post_soup.select_one('.view_content').get_text("\n", strip=True)

        # 텔레그램 발송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>[브리핑 업데이트]</b>\n\n<b>제목: {title}</b>\n\n{content}"
        
        # 텔레그램 글자수 제한(4000자) 대응
        await bot.send_message(chat_id=CHAT_ID, text=message[:4000], parse_mode='HTML')

        # 링크 저장 (다음 중복 체크용)
        with open(last_link_file, "w") as f:
            f.write(post_url)
        print("전송 성공!")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
