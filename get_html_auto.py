import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import csv
from datetime import datetime


def get_quarter(month):
    """월(month)을 기반으로 분기를 계산합니다."""
    return (month - 1) // 3 + 1


def scrape_all_coupang_reviews_sorted(url):
    """
    리뷰를 '최신순'으로 정렬한 후, 모든 리뷰의 날짜와 내용을 수집하여 분기별 CSV 파일로 저장합니다.
    """
    all_reviews_data = []
    driver = None

    try:
        options = uc.ChromeOptions()
        # options.add_argument('--headless') # 브라우저 창 없이 실행하려면 주석 해제
        driver = uc.Chrome(options=options, use_subprocess=True)
        wait = WebDriverWait(driver, 15)
        driver.get(url)

        # 1. 상품평 탭으로 이동
        review_tab_link = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#sdpReview']"))
        )
        driver.execute_script("arguments[0].click();", review_tab_link)
        time.sleep(3)

        # 2. [추가된 로직] '최신순' 버튼 클릭
        try:
            print("리뷰를 '최신순'으로 정렬합니다...")
            # XPath를 사용하여 텍스트가 '최신순'인 버튼을 찾음
            latest_sort_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='최신순']"))
            )
            driver.execute_script("arguments[0].click();", latest_sort_button)
            # 정렬 결과가 로드될 때까지 잠시 대기
            time.sleep(3)
            print("'최신순' 정렬 완료.")
        except Exception as e:
            print(f"최신순 정렬 버튼 클릭 중 오류 발생 (기본 정렬로 진행): {e}")

        # 3. 페이지 순차 이동하며 리뷰 수집
        while True:
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.sdp-review__article__page__num")))
                page_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.sdp-review__article__page__num')
                page_numbers_in_group = [btn.get_attribute("data-page") for btn in page_buttons]

                for page_num in page_numbers_in_group:
                    try:
                        current_page_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[data-page='{page_num}']"))
                        )

                        if 'sdp-review__article__page__num--active' not in current_page_button.get_attribute('class'):
                            driver.execute_script("arguments[0].click();", current_page_button)
                            time.sleep(2)

                        print(f"{page_num}페이지 리뷰를 수집합니다...")

                        html = driver.page_source
                        soup = BeautifulSoup(html, 'html.parser')
                        articles = soup.find_all('article', class_='sdp-review__article__list')

                        for article in articles:
                            date_element = article.find('div',
                                                        class_='sdp-review__article__list__info__product-info__reg-date')
                            review_date = date_element.get_text(strip=True) if date_element else "날짜없음"

                            content_element = article.find('div', class_='sdp-review__article__list__review__content')
                            review_content = content_element.get_text(strip=True) if content_element else ""

                            if review_content:
                                all_reviews_data.append({'date': review_date, 'content': review_content})

                    except Exception as e:
                        print(f"{page_num}페이지 처리 중 오류 발생: {e}")
                        continue

                next_group_button = driver.find_element(By.CSS_SELECTOR,
                                                        'button.sdp-review__article__page__next:not([disabled])')
                print("다음 페이지 그룹으로 이동합니다...")
                driver.execute_script("arguments[0].click();", next_group_button)
                time.sleep(3)
            except NoSuchElementException:
                print("마지막 페이지 그룹입니다. 모든 수집을 종료합니다.")
                break

    except KeyboardInterrupt:
        print("\n사용자에 의해 수집이 중단되었습니다.")
    except Exception as e:
        print(f"크롤링 중 심각한 오류 발생: {e}")

    finally:
        print("\n스크립트를 종료하거나 모든 수집을 완료했습니다. 현재까지 수집된 데이터를 저장합니다...")
        if driver:
            driver.quit()

        if not all_reviews_data:
            print("수집된 리뷰가 없어 저장할 파일이 없습니다.")
            return

        # 4. 수집된 데이터를 분기별로 그룹화 및 CSV 파일로 저장
        reviews_by_quarter = {}
        for review in all_reviews_data:
            try:
                review_date_obj = datetime.strptime(review['date'], '%Y.%m.%d')
                year = review_date_obj.year
                quarter = get_quarter(review_date_obj.month)
                quarter_key = f"{year}_Q{quarter}"
                reviews_by_quarter.setdefault(quarter_key, []).append(review)
            except ValueError:
                reviews_by_quarter.setdefault('날짜형식오류', []).append(review)

        for quarter_key, reviews in reviews_by_quarter.items():
            filename = f"Coupang_Reviews_{quarter_key}.csv"
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Date', 'Review'])
                for review in reviews:
                    writer.writerow([review['date'], review['content']])
            print(f"'{filename}' 파일에 {len(reviews)}개의 리뷰를 저장했습니다.")

        print(f"\n총 {len(all_reviews_data)}개의 리뷰를 {len(reviews_by_quarter)}개의 파일에 나누어 저장 완료했습니다.")


if __name__ == "__main__":
    product_url = input("리뷰를 수집할 쿠팡 제품의 전체 URL을 입력하세요: ")
    if "coupang.com" in product_url:
        scrape_all_coupang_reviews_sorted(product_url)
    else:
        print("유효한 쿠팡 URL이 아닙니다.")