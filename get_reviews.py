import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import sys
import os
from datetime import datetime

# CSS 선택자 상수
REVIEW_TAB_SELECTOR = "a[href='#sdpReview']"
PAGE_BUTTON_SELECTOR = "button.sdp-review__article__page__num"
NEXT_GROUP_BUTTON_SELECTOR = "button.sdp-review__article__page__next:not([disabled])"
REVIEW_ARTICLE_SELECTOR = "sdp-review__article__list"
REVIEW_DATE_CLASS = "sdp-review__article__list__info__product-info__reg-date"
REVIEW_CONTENT_CLASS = "sdp-review__article__list__review__content"

# 기본값 상수
DEFAULT_PRODUCT_ID = "-1"
DEFAULT_DATE = "-1"
WAIT_TIMEOUT = 15
MAX_PAGE_LIMIT = 150  # 최대 페이지 수 제한


def safe_driver_quit(driver):
    """드라이버를 안전 종료"""
    if driver:
        try:
            driver.close()
            driver.quit()
        except Exception:
            pass


def extract_product_id(product_url):
    """URL에서 상품 ID를 추출"""
    try:
        url_parts = product_url.split('/products/')
        if len(url_parts) > 1:
            raw_product_id = url_parts[-1].split('?')[0].split('/')[0].strip()
            
            # ID 유효성 검증
            if raw_product_id and (raw_product_id.replace('-', '').isdigit() or len(raw_product_id) > 3):
                return raw_product_id
            
        return DEFAULT_PRODUCT_ID
    except Exception as e:
        print(f"Product ID 추출 중 오류: {e}")
        return DEFAULT_PRODUCT_ID


def create_chrome_driver():
    """Chrome 드라이버 생성"""
    options = uc.ChromeOptions()
    options.add_argument('--blink-settings=imagesEnabled=false')  # 이미지 비활성화 -> 속도 향상
    options.add_argument('--disable-dev-shm-usage')               # 메모리 관련 오류 방지
    options.add_argument('--no-sandbox')                          # 권한 관련 오류 방지
    
    return uc.Chrome(options=options, use_subprocess=True)


def click_review_tab(driver):
    """리뷰 탭 클릭"""
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    review_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, REVIEW_TAB_SELECTOR)))
    driver.execute_script("arguments[0].click();", review_tab)
    time.sleep(0.5)


def get_page_numbers_in_current_group(driver):
    """현재 페이지 그룹의 페이지 번호 추출"""
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, PAGE_BUTTON_SELECTOR)))
    
    page_buttons = driver.find_elements(By.CSS_SELECTOR, PAGE_BUTTON_SELECTOR)
    return [button.get_attribute("data-page") for button in page_buttons]


def navigate_to_page(driver, page_number):
    """특정 페이지로 이동"""
    page_buttons = driver.find_elements(By.CSS_SELECTOR, f"button[data-page='{page_number}']")
    
    if not page_buttons:
        print(f"{page_number}페이지 버튼을 찾을 수 없어 현재 페이지 그룹 수집을 중단합니다.")
        return False
    
    current_page_button = page_buttons[0]
    
    # 이미 활성화된 페이지가 아니면 클릭
    if 'sdp-review__article__page__num--active' not in current_page_button.get_attribute('class'):
        driver.execute_script("arguments[0].click();", current_page_button)
        time.sleep(0.5)
    
    return True


def extract_reviews_from_current_page(driver, product_id):
    """현재 페이지의 모든 리뷰 추출"""
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, REVIEW_ARTICLE_SELECTOR)))
    
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    review_articles = soup.find_all('article', class_=REVIEW_ARTICLE_SELECTOR)
    reviews_on_page = []
    
    for article in review_articles:
        # 리뷰 날짜 추출
        date_element = article.find('div', class_=REVIEW_DATE_CLASS)
        review_date = date_element.get_text(strip=True) if date_element else DEFAULT_DATE
        
        # 리뷰 내용 추출
        content_element = article.find('div', class_=REVIEW_CONTENT_CLASS)
        review_content = content_element.get_text(strip=True) if content_element else ""
        
        # 유효한 리뷰만 추가
        if review_content:
            reviews_on_page.append({
                'ProductID': product_id,
                'Date': review_date,
                'Review': review_content
            })
    
    return reviews_on_page


def has_next_page_group(driver):
    """다음 페이지 그룹이 있는지 확인하고 이동"""
    try:
        next_group_button = driver.find_element(By.CSS_SELECTOR, NEXT_GROUP_BUTTON_SELECTOR)
        print("다음 페이지 그룹으로 이동합니다...")
        driver.execute_script("arguments[0].click();", next_group_button)
        time.sleep(0.5)
        return True
    except NoSuchElementException:
        print("마지막 페이지 그룹입니다. 상품 리뷰 수집을 종료합니다.")
        return False



def read_url_list(file_path):
    """텍스트 파일에서 URL 목록을 읽어옴"""
    if not os.path.exists(file_path):
        print(f"{file_path} 파일을 찾을 수 없습니다.")
        print(f"{file_path} 파일을 생성하고 쿠팡 상품 URL을 한 줄씩 작성해주세요.")
        return []
    
    urls = []
    line_number = 1
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "coupang.com" in line:
                        clean_url = line.split('?')[0]  # 쿼리 파라미터 제거
                        urls.append(clean_url)
                    else:
                        print(f"경고: 줄 {line_number} - 유효하지 않은 쿠팡 URL을 건너뜁니다: {line}")
                line_number += 1
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return []
    
    return urls


def process_single_product(product_url, product_index, total_products, driver):
    """단일 상품의 리뷰를 수집"""
    print(f"\n{'='*60}")
    print(f"[{product_index}/{total_products}] 상품 리뷰 수집 시작")
    print(f"URL: {product_url}")
    print(f"{'='*60}")
    
    try:
        # 상품 페이지로 이동
        print(f"상품 페이지에 접속합니다...")
        driver.get(product_url)
        WebDriverWait(driver, WAIT_TIMEOUT)
        time.sleep(1)
        
        # 상품 ID 추출
        product_id = extract_product_id(product_url)
        print(f"Product ID: {product_id}")
        
        # 리뷰 탭으로 이동
        click_review_tab(driver)
        
        all_reviews = []
        
        # 모든 페이지 그룹 순회
        while True:
            page_numbers = get_page_numbers_in_current_group(driver)
            
            # 현재 그룹의 각 페이지 순회
            for page_number in page_numbers:
                try:
                    # 최대 페이지 확인
                    if int(page_number) >= MAX_PAGE_LIMIT:
                        print(f"최대 페이지 제한({MAX_PAGE_LIMIT})에 도달했습니다. 다음 상품으로 이동합니다.")
                        return pd.DataFrame(all_reviews) if all_reviews else pd.DataFrame(columns=['ProductID', 'Date', 'Review'])
                    
                    # 페이지 이동
                    if not navigate_to_page(driver, page_number):
                        break
                    
                    print(f"  -> {page_number}페이지 리뷰 수집 중...")
                    
                    # 현재 페이지의 리뷰 수집
                    reviews_on_page = extract_reviews_from_current_page(driver, product_id)
                    all_reviews.extend(reviews_on_page)
                    
                except KeyboardInterrupt:
                    print("\n수집이 중단되었습니다.")
                    raise
                except Exception as e:
                    print(f"  -> {page_number}페이지 처리 중 오류 발생: {e}")
                    continue
            
            # 다음 페이지 그룹 확인 및 이동
            try:
                if not has_next_page_group(driver):
                    break
            except KeyboardInterrupt:
                print("\n수집이 중단되었습니다.")
                raise
        
        # DataFrame 변환 및 반환
        if all_reviews:
            reviews_df = pd.DataFrame(all_reviews)
            print(f"  -> 총 {len(reviews_df)}개의 리뷰를 수집했습니다.")
            return reviews_df
        else:
            print("  -> 수집된 리뷰가 없습니다.")
            return pd.DataFrame(columns=['ProductID', 'Date', 'Review'])
            
    except Exception as e:
        print(f"상품 처리 중 오류 발생: {e}")
        return pd.DataFrame(columns=['ProductID', 'Date', 'Review'])


def generate_output_filename(product_id):
    """출력 파일명 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Coupang_Reviews_{product_id}_{timestamp}.csv"


def save_reviews_to_csv(reviews_df, output_filename):
    """리뷰 데이터를 CSV 파일로 저장"""
    reviews_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"리뷰 데이터가 '{output_filename}' 파일에 저장되었습니다.")




def main():
    """메인 실행 함수 - 배치 처리 방식"""
    print("="*60)
    print("🛍️ 쿠팡 리뷰 수집기 (배치 처리)")
    print("="*60)
    
    try:
        # 사용법 안내
        if len(sys.argv) == 1:
            print("사용법:")
            print("  단일 URL 처리: python get_reviews.py <product_url>")
            print("  배치 처리:     python get_reviews.py <url_list_file.txt>")
            print("\n예시:")
            print("  python get_reviews.py https://www.coupang.com/vp/products/123456789")
            print("  python get_reviews.py coupang_list.txt")
            return
        
        # 첫 번째 인자 분석
        first_arg = sys.argv[1]
        
        if "coupang.com" in first_arg:
            # 단일 URL 처리 모드
            clean_url = first_arg.split('?')[0]
            product_urls = [clean_url]
            print(f"단일 상품 처리 모드")
            print(f"대상 상품: {clean_url}")
        else:
            # 배치 처리 모드 (텍스트 파일에서 읽기)
            list_file = first_arg
            print(f"배치 처리 모드 - {list_file}에서 URL 목록을 읽습니다...")
            product_urls = read_url_list(list_file)
            
            if not product_urls:
                print("처리할 URL이 없습니다. 프로그램을 종료합니다.")
                return
            
            print(f"총 {len(product_urls)}개의 상품을 처리합니다.")
        
        print("="*60)
        
        # Chrome 드라이버 한 번만 초기화
        driver = None
        success_count = 0
        fail_count = 0
        total_reviews = 0
        
        try:
            print("Chrome 드라이버를 초기화합니다...")
            driver = create_chrome_driver()
            print("✅ 드라이버 초기화 완료!\n")
            
            # 각 상품 순차 처리
            for index, product_url in enumerate(product_urls, 1):
                try:
                    # 상품별 리뷰 수집
                    reviews_df = process_single_product(product_url, index, len(product_urls), driver)
                    
                    if not reviews_df.empty:
                        # CSV 파일로 저장
                        product_id = reviews_df.iloc[0]['ProductID']
                        output_filename = generate_output_filename(product_id)
                        save_reviews_to_csv(reviews_df, output_filename)
                        
                        success_count += 1
                        total_reviews += len(reviews_df)
                        print(f"  ✅ 성공: {len(reviews_df)}개 리뷰 → {output_filename}")
                    else:
                        fail_count += 1
                        print(f"  ❌ 실패: 수집된 리뷰가 없습니다.")
                    
                    # 다음 상품으로 넘어가기 전 잠시 대기
                    if index < len(product_urls):
                        print("  💤 다음 상품 처리를 위해 3초 대기 중...\n")
                        time.sleep(3)
                        
                except KeyboardInterrupt:
                    print(f"\n사용자에 의해 작업이 중단되었습니다.")
                    break
                except Exception as e:
                    fail_count += 1
                    print(f"  ❌ 상품 처리 실패: {e}\n")
                    continue
            
        finally:
            # 드라이버 종료
            safe_driver_quit(driver)
        
        # 최종 결과 요약
        print("="*60)
        print("🎉 배치 작업 완료!")
        print("="*60)
        print("📊 작업 결과 요약:")
        print(f"   - 총 처리 대상: {len(product_urls)}개")
        print(f"   - 성공: {success_count}개")
        print(f"   - 실패: {fail_count}개")
        print(f"   - 총 수집 리뷰: {total_reviews:,}개")
        print(f"   - 성공률: {(success_count/len(product_urls)*100):.1f}%")
        
        if fail_count > 0:
            print(f"\n⚠️  일부 작업이 실패했습니다. 로그를 확인해주세요.")
            
    except KeyboardInterrupt:
        print("\n작업이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()