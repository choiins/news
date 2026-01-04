import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import os

# 언론사 정보
NEWSPAPERS = {
    "종합지": {
        "조선일보": {"code": "023", "url": "https://media.naver.com/press/023/newspaper?date="},
        "중앙일보": {"code": "353", "url": "https://media.naver.com/press/353/newspaper?date="},
        "동아일보": {"code": "020", "url": "https://media.naver.com/press/020/newspaper?date="},
        "한겨레": {"code": "028", "url": "https://media.naver.com/press/028/newspaper?date="},
        "경향신문": {"code": "032", "url": "https://media.naver.com/press/032/newspaper?date="},
        "한국일보": {"code": "469", "url": "https://media.naver.com/press/469/newspaper?date="},
        "국민일보": {"code": "005", "url": "https://media.naver.com/press/005/newspaper?date="},
        "서울신문": {"code": "081", "url": "https://media.naver.com/press/081/newspaper?date="},
    },
    "경제지": {
        "매일경제": {"code": "009", "url": "https://media.naver.com/press/009/newspaper?date="},
        "한국경제": {"code": "015", "url": "https://media.naver.com/press/015/newspaper?date="},
        "서울경제": {"code": "011", "url": "https://media.naver.com/press/011/newspaper?date="},
        "머니투데이": {"code": "008", "url": "https://media.naver.com/press/008/newspaper?date="},
    }
}

def scrape_newspaper_page(newspaper_name, url, date_str):
    """
    특정 언론사 페이지에서 1면(A1) 기사 정보 수집
    
    Args:
        newspaper_name: 언론사 이름
        url: 언론사 페이지 URL (날짜 제외)
        date_str: 날짜 문자열 (YYYYMMDD)
    
    Returns:
        dict: 언론사 이름, 기사 리스트, 페이지 URL
    """
    full_url = url + date_str
    print(f"\n[{newspaper_name}] 접속 중: {full_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(full_url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # A1면 섹션 찾기
        # 구조: <div class="newspaper_inner"> 안에 <h3><span class="page_notation"><em>A1</em>면</span></h3>와
        # <ul class="newspaper_article_lst"> 안에 기사들이 있음
        newspaper_inner_divs = soup.find_all('div', class_='newspaper_inner')
        
        a1_section = None
        for div in newspaper_inner_divs:
            # A1면 표시를 찾기
            page_notation = div.find('h3')
            if page_notation:
                page_span = page_notation.find('span', class_='page_notation')
                if page_span:
                    em_tag = page_span.find('em')
                    if em_tag and em_tag.get_text(strip=True) == 'A1':
                        a1_section = div
                        break
        
        if a1_section:
            # A1 섹션 내의 ul.newspaper_article_lst 찾기
            article_list = a1_section.find('ul', class_='newspaper_article_lst')
            
            if article_list:
                # ul 안의 모든 li 태그를 순서대로 찾기 (상단에서 하단)
                list_items = article_list.find_all('li')
                
                for li in list_items:
                    # li 안의 a 태그 찾기
                    link = li.find('a', href=True)
                    
                    if link:
                        # 제목은 strong 태그 안에 있음
                        strong_tag = link.find('strong')
                        if strong_tag:
                            title = strong_tag.get_text(strip=True)
                        else:
                            # strong이 없으면 a 태그의 전체 텍스트 사용
                            title = link.get_text(strip=True)
                        
                        href = link.get('href', '')
                        
                        # 제목이 있는 경우만 추가
                        if title:
                            # URL이 이미 완전한 URL인 경우 그대로 사용
                            if href.startswith('http'):
                                article_url = href
                            elif href.startswith('/'):
                                article_url = f"https://news.naver.com{href}"
                            else:
                                continue
                            
                            articles.append({
                                'title': title,
                                'link': article_url
                            })
        
        print(f"  ✓ 총 {len(articles)}개의 A1면 기사 수집 완료")
        
        return {
            "newspaper": newspaper_name,
            "articles": articles,
            "page_url": full_url
        }
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "newspaper": newspaper_name,
            "articles": [],
            "page_url": full_url,
            "error": str(e)
        }

def send_to_telegram(bot_token, chat_id, message):
    """텔레그램으로 메시지 전송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True, "메시지 전송 성공"
    except Exception as e:
        return False, f"전송 실패: {str(e)}"

def format_telegram_message(newspaper_data):
    """
    언론사별 데이터를 텔레그램 메시지 형식으로 변환
    
    Args:
        newspaper_data: scrape_newspaper_page의 반환값
    
    Returns:
        str: 포맷된 텔레그램 메시지
    """
    newspaper_name = newspaper_data['newspaper']
    articles = newspaper_data['articles']
    page_url = newspaper_data['page_url']
    
    message = f"<b>{newspaper_name}</b>\n\n"
    
    if articles:
        for article in articles:
            message += f"{article['title']}\n"
            message += f"{article['link']}\n\n"
    else:
        message += "기사를 찾을 수 없습니다.\n\n"
    
    message += f"<a href='{page_url}'>지면 보기</a>"
    
    return message

def main():
    """메인 함수"""
    # 오늘 날짜
    today = datetime.now().strftime('%Y%m%d')
    print(f"오늘 날짜: {today}")
    
    all_results = {}
    
    try:
        # 모든 언론사 순회
        for category, newspapers in NEWSPAPERS.items():
            print(f"\n{'='*60}")
            print(f"{category} 수집 시작")
            print(f"{'='*60}")
            
            category_results = {}
            
            for newspaper_name, info in newspapers.items():
                result = scrape_newspaper_page(
                    newspaper_name, 
                    info['url'], 
                    today
                )
                category_results[newspaper_name] = result
                time.sleep(1)  # 요청 간 대기
            
            all_results[category] = category_results
        
        # 결과를 JSON으로 저장
        output_filename = f"newspaper_results_{today}.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 결과가 {output_filename}에 저장되었습니다.")
        
        # 텔레그램으로 전송
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if bot_token and chat_id:
            print("\n텔레그램으로 전송 중...")
            
            for category, newspapers in all_results.items():
                for newspaper_name, newspaper_data in newspapers.items():
                    if newspaper_data.get('articles'):
                        message = format_telegram_message(newspaper_data)
                        success, result_msg = send_to_telegram(bot_token, chat_id, message)
                        if success:
                            print(f"  ✅ {newspaper_name} 전송 완료")
                        else:
                            print(f"  ❌ {newspaper_name} 전송 실패: {result_msg}")
                        time.sleep(1)  # API 요청 간 대기
            
            print("\n✅ 모든 메시지 전송 완료!")
        else:
            print("\n💡 텔레그램 전송을 위해 환경 변수를 설정하세요:")
            print("   export TELEGRAM_BOT_TOKEN='your_bot_token'")
            print("   export TELEGRAM_CHAT_ID='your_chat_id'")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

