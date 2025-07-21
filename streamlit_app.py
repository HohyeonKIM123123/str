import streamlit as st

import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup, Tag
from datetime import datetime
import os

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_int(text):
    if not text:
        return None
    nums = re.findall(r'\d+', text.replace(',', ''))
    return int(nums[0]) if nums else None

def crawl_monthler_real(max_count=100):
    driver = setup_driver()
    data = []
    try:
        driver.get("https://www.monthler.kr/")
        time.sleep(3)
        # 카드가 뜰 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
        # 더보기 반복
        while True:
            try:
                more_btn = driver.find_element(By.XPATH, "//button[contains(text(), '더 보기') or contains(text(), '더보기')]")
                driver.execute_script("arguments[0].click();", more_btn)
                time.sleep(1.5)
                if len(driver.find_elements(By.CSS_SELECTOR, "article")) >= max_count:
                    break
            except Exception:
                break

        cards = driver.find_elements(By.CSS_SELECTOR, "article")
        for i, card in enumerate(cards[:max_count]):
            try:
                html = card.get_attribute('outerHTML') or ""
                soup = BeautifulSoup(html, 'html.parser')
                
                # 숙소명
                name = soup.find('h4') or soup.find('h3') or soup.find('h5') or soup.find('strong')
                name = name.get_text(strip=True) if name else f"숙소 {i+1}"
                
                # 이미지
                img = soup.find('img')
                img_url = img['src'] if img and isinstance(img, Tag) and img.has_attr('src') else ""
                if str(img_url).startswith('/'):
                    img_url = f"https://www.monthler.kr{img_url}"
                
                # D-day, 지원자수, 지역(카드에서)
                dday = None
                applicants = None
                region = ""
                
                dday_elem = soup.find('span', class_=re.compile('ProgramCard_dday'))
                if dday_elem:
                    dday_text = dday_elem.get_text(strip=True)
                    if 'D-' in dday_text:
                        dday = extract_int(dday_text)
                    elif '마감' in dday_text:
                        dday = 0
                
                applicants_elem = soup.find('div', class_=re.compile('ProgramCard_applicantsNumber'))
                if applicants_elem:
                    applicants = extract_int(applicants_elem.get_text())
                
                region_elem = soup.find('p', class_=re.compile('ProgramCard_txt_detail'))
                if region_elem:
                    region = region_elem.get_text(strip=True)
                
                # 카드에서 추가 정보 추출
                모집기간 = ""
                모집인원 = ""
                활동기간 = ""
                지원금 = ""
                카테고리 = ""
                상세설명 = ""
                
                # 지원금 정보 찾기 (ProgramCard_txt_subsidy 클래스)
                subsidy_elem = soup.find('div', class_=re.compile('ProgramCard_txt_subsidy'))
                if subsidy_elem:
                    지원금 = subsidy_elem.get_text(strip=True)
                
                # 모집기간 찾기 (ProgramCard_txt_detail 클래스 중 날짜 패턴)
                detail_elems = soup.find_all('div', class_=re.compile('ProgramCard_txt_detail'))
                for elem in detail_elems:
                    text = elem.get_text(strip=True)
                    if re.search(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일', text):
                        모집기간 = text
                        break
                
                # 지역 정보 찾기 (ProgramCard_txt_detail 클래스 중 지역)
                region_elems = soup.find_all('p', class_=re.compile('ProgramCard_txt_detail'))
                for elem in region_elems:
                    text = elem.get_text(strip=True)
                    if text and not re.search(r'\d{4}년', text):  # 날짜가 아닌 텍스트
                        region = text
                        break
                
                # 댓글/설명 찾기 (카드 하단의 댓글 영역)
                comment_elem = soup.find('div', class_=re.compile('inline-flex.*items-center.*mt-3'))
                if comment_elem:
                    comment_text = comment_elem.get_text(strip=True)
                    if comment_text and len(comment_text) > 10:  # 의미있는 텍스트만
                        상세설명 = comment_text
                
                # 모집상태
                모집상태 = ""
                if dday_elem:
                    모집상태 = dday_elem.get_text(strip=True)
                
                card_data = {
                    'name': name,
                    'img_url': img_url,
                    'region': region,
                    'dday': dday,
                    'applicants': applicants,
                    '모집기간': 모집기간,
                    '모집인원': 모집인원,
                    '활동기간': 활동기간,
                    '지원금': 지원금,
                    '카테고리': 카테고리,
                    '상세설명': 상세설명,
                    '연락처': "",
                    '모집상태': 모집상태,
                    'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                data.append(card_data)
                print(f"카드 {i+1} 처리 완료: {name}")
                
            except Exception as e:
                print(f"카드 {i+1} 처리 오류: {name if 'name' in locals() else ''}, 에러: {e}")
                continue
        print(f"총 {len(data)}개 프로그램 데이터 수집 완료")
    finally:
        driver.quit()
    return data

def main():
    print("=== 한달살러 프로그램 데이터 크롤링 시작 ===")
    data = crawl_monthler_real(max_count=10)
    df = pd.DataFrame(data)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "monthler_processed.csv")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"파일 저장: {output_file}")
    print(df.head())

if __name__ == "__main__":
    main()

