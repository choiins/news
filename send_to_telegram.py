import json
import re
import time
import os
import requests


def _clean_title_keep_specific_tag(title: str, keep_tag: str = '단독') -> str:
    # Remove all bracketed tags except when the inner text equals keep_tag
    def repl(m):
        inner = m.group(0)[1:-1].strip()
        return m.group(0) if inner == keep_tag else ''
    return re.sub(r"\[.*?\]", repl, title).strip()


def send_news_results_to_telegram(bot_token: str, chat_id: str, json_file_path: str,
                                  keep_tag: str = '단독', chunk_size: int = 10,
                                  pause: float = 0.5) -> (bool, str):
    """Send cleaned title+link pairs from a JSON file to Telegram in chunks.

    Expects the JSON file to be a list of objects with `title` and `link` keys.
    """
    if not os.path.exists(json_file_path):
        return False, f"JSON 파일을 찾을 수 없습니다: {json_file_path}"

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except Exception as e:
        return False, f"JSON 읽기 실패: {e}"

    texts = []
    for it in items:
        title = it.get('title', '')
        link = it.get('link', '')
        clean = _clean_title_keep_specific_tag(title, keep_tag=keep_tag)
        if not clean:
            clean = title.strip()
        texts.append(f"{clean}\n{link}")

    send_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    sent = 0
    try:
        for i in range(0, len(texts), chunk_size):
            chunk = "\n\n".join(texts[i:i+chunk_size])
            resp = requests.post(send_url, data={'chat_id': chat_id, 'text': chunk})
            if resp.status_code != 200:
                return False, f"텔레그램 전송 실패: {resp.status_code} {resp.text}"
            sent += 1
            time.sleep(pause)
    except Exception as e:
        return False, f"텔레그램 전송 중 오류: {e}"

    return True, f"전송 완료: {len(texts)} 항목을 {sent}개의 메시지로 전송했습니다."


if __name__ == '__main__':
    # quick CLI for testing
    bot = os.getenv('TELEGRAM_BOT_TOKEN')
    chat = os.getenv('TELEGRAM_CHAT_ID')
    import sys
    if not bot or not chat or len(sys.argv) < 2:
        print("사용법: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 환경변수 설정 후\npython send_to_telegram.py path/to/file.json")
        sys.exit(1)
    ok, msg = send_news_results_to_telegram(bot, chat, sys.argv[1])
    print(ok, msg)
