import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

async def main():
    list_url = "https://www.thewm.co.kr/news/list.asp?sid=N99"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(list_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        first_post = soup.select_one('table.board_list tbody tr a')
        if not first_post: return
        
        post_url = "https://www.thewm.co.kr/news/" + first_post['href']

        # 중복 체크: 마지막으로 보낸 링크인지 확인
        last_link_file = "last_link.txt"
        if os.path.exists(last_link_file):
            with open(last_link_file, "r") as f:
                if f.read().strip() == post_url:
                    print("새 글 없음")
                    return

        # 본문 내용 추출
        post_res = requests.get(post_url, headers=headers)
        post_soup = BeautifulSoup(post_res.text, 'html.parser')
        title = post_soup.select_one('.view_title').get_text(strip=True)
        content = post_soup.select_one('.view_content').get_text("\n", strip=True)

        # 텔레그램 전송
        bot = telegram.Bot(token=TOKEN)
        message = f"<b>[신규 업데이트]</b>\n\n<b>제목: {title}</b>\n\n{content}"
        await bot.send_message(chat_id=CHAT_ID, text=message[:4000], parse_mode='HTML')

        # 링크 저장
        with open(last_link_file, "w") as f:
            f.write(post_url)
        
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
