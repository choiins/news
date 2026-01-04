import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict
import os

# 네이버 뉴스 섹션 정보
SECTIONS = {
    "100": "정치",
    "101": "사회",
    "103": "경제",
    "104": "세계",
    "105": "IT/과학"
}

# 텔레그램 설정 (환경변수에서 가져오기, 없으면 기본값 사용)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8571818489:AAEjJ_XElYIHPduHgMbmhQ1RbmVhWK6CEUo")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6355937482")


def get_news_from_section(section_id: str, section_name: str) -> List[Dict[str, str]]:
    """
    특정 섹션에서 '단독'이 포함된 기사를 수집합니다.
    
    Args:
        section_id: 섹션 ID (예: "100")
        section_name: 섹션 명칭 (예: "정치")
    
    Returns:
        제목과 URL이 포함된 딕셔너리 리스트
    """
    url = f"https://news.naver.com/section/{section_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # 네이버 뉴스 섹션 페이지의 기사 구조에 맞게 파싱
        # 일반적으로 기사는 a 태그로 감싸져 있고, 제목은 텍스트로 포함됨
        news_items = soup.find_all('a', class_='sa_text_title')
        
        # 다른 가능한 선택자들도 시도
        if not news_items:
            news_items = soup.find_all('a', href=lambda x: x and '/article/' in x)
        
        for item in news_items:
            title = item.get_text(strip=True)
            link = item.get('href', '')
            
            # '단독'이 제목에 포함된 경우만 수집
            if '단독' in title:
                # 상대 경로인 경우 절대 경로로 변환
                if link.startswith('/'):
                    link = f"https://news.naver.com{link}"
                elif not link.startswith('http'):
                    continue
                
                articles.append({
                    'title': title,
                    'url': link,
                    'section': section_name
                })
        
        return articles
    
    except Exception as e:
        print(f"섹션 {section_name} ({section_id}) 수집 중 오류 발생: {e}")
        return []


def send_to_telegram(articles_by_section: Dict[str, List[Dict[str, str]]]) -> bool:
    """
    수집된 기사들을 텔레그램으로 전송합니다.
    
    Args:
        articles_by_section: 섹션별로 그룹화된 기사 딕셔너리
    
    Returns:
        전송 성공 여부
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("텔레그램 설정이 없습니다. TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 환경변수를 설정해주세요.")
        return False
    
    message_parts = []
    message_parts.append("네이버 뉴스 '단독' 기사 수집 결과\n")
    message_parts.append("=" * 40 + "\n")
    
    total_count = 0
    
    for section_name, articles in articles_by_section.items():
        if articles:
            message_parts.append(f"\n[{section_name}] 섹션\n")
            
            for article in articles:
                message_parts.append(f"{article['title']}\n")
                message_parts.append(f"{article['url']}\n\n")
            
            total_count += len(articles)
            message_parts.append("-" * 40 + "\n")
    
    if total_count == 0:
        message_parts.append("\n'단독'이 포함된 기사를 찾을 수 없습니다.\n")
    
    message = "".join(message_parts)
    
    # 텔레그램 메시지 길이 제한 (4096자) 처리
    if len(message) > 4096:
        # 섹션별로 나눠서 전송
        for section_name, articles in articles_by_section.items():
            if articles:
                section_message = f"[{section_name}] 섹션\n\n"
                for article in articles:
                    section_message += f"{article['title']}\n{article['url']}\n\n"
                
                if len(section_message) > 4096:
                    # 기사별로 나눠서 전송
                    for article in articles:
                        article_message = f"[{section_name}]\n\n{article['title']}\n{article['url']}"
                        send_telegram_message(article_message)
                else:
                    send_telegram_message(section_message)
                time.sleep(1)  # API 호출 제한을 위한 대기
    else:
        send_telegram_message(message)
    
    return True


def send_telegram_message(text: str) -> bool:
    """
    텔레그램으로 메시지를 전송합니다.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"텔레그램 전송 중 오류 발생: {e}")
        return False


def main():
    """
    메인 함수: 모든 섹션에서 '단독' 기사를 수집하고 텔레그램으로 전송합니다.
    """
    print("네이버 뉴스 섹션별 '단독' 기사 수집을 시작합니다...")
    
    all_articles_by_section = {}
    
    for section_id, section_name in SECTIONS.items():
        print(f"\n[{section_name}] 섹션 수집 중...")
        articles = get_news_from_section(section_id, section_name)
        
        if articles:
            all_articles_by_section[section_name] = articles
            print(f"  → {len(articles)}건의 '단독' 기사 발견")
        else:
            print(f"  → '단독' 기사 없음")
        
        # 서버 부하를 줄이기 위한 대기
        time.sleep(1)
    
    # 텔레그램으로 전송
    if all_articles_by_section:
        print("\n텔레그램으로 전송 중...")
        send_to_telegram(all_articles_by_section)
        print("전송 완료!")
    else:
        print("\n수집된 기사가 없습니다.")


if __name__ == "__main__":
    main()

