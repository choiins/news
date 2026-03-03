from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import json
import os
from datetime import datetime

def scrape_naver_news():
    # Chrome 옵션 설정
    chrome_options = Options()
    # chrome_options.add_argument('--headless')  # 브라우저 창을 띄우지 않음 (필요시 제거)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent 설정
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 드라이버 초기화
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # URL 접속
        url = "https://search.naver.com/search.naver?ssc=tab.news.all&query=%EB%8B%A8%EB%8F%85&sm=tab_opt&sort=1&photo=0&field=0&pd=0&ds=2025.12.26&de=2025.12.26&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Add%2Cp%3Aall&is_sug_officeid=0&office_category=0&service_area=1"
        print(f"접속 중: {url}")
        driver.get(url)
        time.sleep(2)  # 페이지 로딩 대기
        
        # 스크롤 다운을 20번 반복
        print("스크롤 다운 시작...")
        for i in range(20):
            # 페이지 끝까지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)  # 0.5초 대기
            print(f"스크롤 {i+1}/20 완료")
        
        # 뉴스 검색 결과 찾기
        # 셀렉터가 동적일 수 있으므로 여러 방법 시도
        news_items = []
        
        # 뉴스 기사 요소 찾기 (여러 방법 시도)
        news_elements = []
        
        # 방법 1: 클래스명으로 직접 찾기
        try:
            news_elements = driver.find_elements(By.CSS_SELECTOR, "div.shjpbJ1U8dIwWXdtD0kq")
            if not news_elements:
                # 방법 2: 더 일반적인 셀렉터 사용
                news_elements = driver.find_elements(By.CSS_SELECTOR, "div.sds-comps-vertical-layout.sds-comps-full-layout")
        except:
            # 방법 3: data-heatmap-target 속성으로 찾기
            try:
                news_elements = driver.find_elements(By.CSS_SELECTOR, "a[data-heatmap-target='.tit']")
                # 부모 요소로 변환
                news_elements = [elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'sds-comps-vertical-layout')]") for elem in news_elements]
            except:
                pass
        
        print(f"총 {len(news_elements)}개의 뉴스 요소 발견")
        
        # 중복 제거를 위한 set
        seen_links = set()
        
        # 각 뉴스 기사에서 제목과 링크 추출
        for idx, element in enumerate(news_elements):
            try:
                # 제목 찾기 (여러 방법 시도)
                title = None
                link = None
                
                # 제목 추출 시도 (여러 방법)
                try:
                    # 방법 1: data-heatmap-target='.tit' 속성을 가진 링크의 텍스트
                    title_element = element.find_element(By.CSS_SELECTOR, "a[data-heatmap-target='.tit']")
                    title = title_element.text.strip()
                    # 링크도 함께 가져오기
                    link = title_element.get_attribute('href')
                except:
                    try:
                        # 방법 2: headline1 클래스를 가진 span
                        title_element = element.find_element(By.CSS_SELECTOR, "span.sds-comps-text-type-headline1")
                        title = title_element.text.strip()
                        # 부모 링크 찾기
                        link_element = title_element.find_element(By.XPATH, "./ancestor::a")
                        link = link_element.get_attribute('href')
                    except:
                        try:
                            # 방법 3: 일반적인 제목 링크
                            title_element = element.find_element(By.CSS_SELECTOR, "a[target='_blank'] span.sds-comps-text-type-headline1")
                            title = title_element.text.strip()
                            link_element = title_element.find_element(By.XPATH, "./ancestor::a")
                            link = link_element.get_attribute('href')
                        except:
                            # 방법 4: 모든 링크를 확인하여 뉴스 링크 찾기
                            link_elements = element.find_elements(By.CSS_SELECTOR, "a[target='_blank']")
                            for link_elem in link_elements:
                                href = link_elem.get_attribute('href')
                                if href and ('news.naver.com' in href or any(domain in href for domain in ['.kr', '.com'])):
                                    # 링크 텍스트에서 제목 추출 시도
                                    try:
                                        title = link_elem.find_element(By.CSS_SELECTOR, "span").text.strip()
                                        link = href
                                        break
                                    except:
                                        pass
                
                # 제목에 '단독'이 포함되고, 중복되지 않은 경우만 저장
                if title and '단독' in title and link and link not in seen_links:
                    seen_links.add(link)
                    news_items.append({
                        "title": title,
                        "link": link
                    })
                    print(f"[{len(news_items)}] {title[:50]}...")
                
            except Exception as e:
                print(f"기사 {idx+1} 처리 중 오류: {str(e)}")
                continue
        
        # JSON 파일로 저장
        output_filename = f"naver_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(news_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n총 {len(news_items)}개의 '단독' 기사를 찾았습니다.")
        print(f"결과가 {output_filename}에 저장되었습니다.")
        
        # 텔레그램으로 전송 (환경 변수가 설정된 경우)
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if bot_token and chat_id:
            print("\n텔레그램으로 결과 전송 중...")
            try:
                from send_to_telegram import send_news_results_to_telegram
                success, message = send_news_results_to_telegram(bot_token, chat_id, output_filename)
                if success:
                    print(f"✅ {message}")
                else:
                    print(f"❌ {message}")
            except ImportError:
                print("❌ send_to_telegram 모듈을 찾을 수 없습니다.")
            except Exception as e:
                print(f"❌ 텔레그램 전송 중 오류: {str(e)}")
        else:
            print("\n💡 텔레그램으로 결과를 받으려면 환경 변수를 설정하세요:")
            print("   export TELEGRAM_BOT_TOKEN='여기에 토큰값을 넣으세요'")
            print("   export TELEGRAM_CHAT_ID='여기에 ID값을 넣으세요'")
        
        
        
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_naver_news()

