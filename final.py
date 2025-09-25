import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
import csv
from datetime import datetime
from urllib.parse import urljoin


## [제거] 분기별 저장을 하지 않으므로 get_quarter 함수를 제거했습니다.

## [수정] 함수가 파일 저장을 하지 않고, 수집한 리뷰 데이터만 반환하도록 변경했습니다.
def scrape_reviews_from_current_page(driver):
    """현재 페이지의 리뷰를 수집하여 리스트 형태로 반환합니다."""
    all_reviews_data = []
    wait = WebDriverWait(driver, 15)

    try:
        review_tab_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#sdpReview']")))
        driver.execute_script("arguments[0].click();", review_tab_link)
        time.sleep(0.5)

        while True:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.sdp-review__article__page__num")))
            page_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.sdp-review__article__page__num')
            page_numbers_in_group = [btn.get_attribute("data-page") for btn in page_buttons]

            for page_num in page_numbers_in_group:
                try:
                    page_button_to_click_list = driver.find_elements(By.CSS_SELECTOR, f"button[data-page='{page_num}']")
                    if not page_button_to_click_list:
                        print(f"{page_num}페이지 버튼을 찾을 수 없어 현재 페이지 그룹 수집을 중단합니다.")
                        break

                    page_button_to_click = page_button_to_click_list[0]

                    if 'sdp-review__article__page__num--active' not in page_button_to_click.get_attribute('class'):
                        driver.execute_script("arguments[0].click();", page_button_to_click)
                        time.sleep(0.5)

                    print(f"{page_num}페이지 리뷰를 수집합니다...")

                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sdp-review__article__list")))
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

            try:
                next_group_button = driver.find_element(By.CSS_SELECTOR,
                                                        'button.sdp-review__article__page__next:not([disabled])')
                print("다음 페이지 그룹으로 이동합니다...")
                driver.execute_script("arguments[0].click();", next_group_button)
                time.sleep(0.5)
            except NoSuchElementException:
                print("마지막 페이지 그룹입니다. 상품 리뷰 수집을 종료합니다.")
                break

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"리뷰 수집 중 심각한 오류 발생: {e}")

    return all_reviews_data


if __name__ == "__main__":
    start_url = input("리뷰를 수집할 첫 번째 쿠팡 제품의 전체 URL을 입력하세요: ")

    max_products = None
    try:
        max_products_input = input("수집할 최대 상품 개수를 입력하세요 (전체 수집은 그냥 Enter): ")
        if max_products_input:
            max_products = int(max_products_input)
    except ValueError:
        print("잘못된 입력입니다. 전체 상품을 수집합니다.")
        max_products = None

    ## [수정] 단일 CSV 파일 생성 및 헤더 작성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"Coupang_Reviews_{timestamp}.csv"

    with open(output_filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['ProductID', 'Date', 'Review'])
    print(f"모든 리뷰는 '{output_filename}' 파일에 통합 저장됩니다.")

    ## [수정] URL 대기열 대신 'current_url'을 직접 관리하여 루프를 실행합니다.
    current_url = start_url.split('?')[0]
    scraped_urls = set()
    driver = None
    products_scraped_count = 0

    try:
        options = uc.ChromeOptions()
        options.add_argument('--blink-settings=imagesEnabled=false')
        driver = uc.Chrome(options=options, use_subprocess=True)

        while current_url and (max_products is None or products_scraped_count < max_products):
            if "coupang.com" not in current_url:
                print(f"유효한 쿠팡 URL이 아닙니다: {current_url}")
                break

            scraped_urls.add(current_url)
            products_scraped_count += 1
            print(
                f"\n{'=' * 50}\n[ {products_scraped_count} / {max_products if max_products else '∞'} 번째 상품 리뷰 수집 시작 ]\nURL: {current_url}\n{'=' * 50}")

            driver.get(current_url)
            time.sleep(1)

            ## [추가] URL에서 Product ID를 추출합니다.
            try:
                product_id = current_url.split('/products/')[-1].strip()
                if not product_id.isdigit():  # ID가 숫자가 아니면 예외 처리
                    product_id = "ID_추출실패"
            except:
                product_id = "ID_추출실패"

            reviews_data = scrape_reviews_from_current_page(driver)

            ## [수정] 수집된 리뷰를 단일 파일에 '추가'합니다.
            if reviews_data:
                with open(output_filename, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    for review in reviews_data:
                        writer.writerow([product_id, review['date'], review['content']])
                print(f"-> 상품 ID [{product_id}]의 리뷰 {len(reviews_data)}개를 파일에 추가했습니다.")
            else:
                print(f"-> 상품 ID [{product_id}]에서 수집된 리뷰가 없습니다.")

            ## [수정] 다음 URL을 효율적으로 탐색합니다.
            print("\n다음 수집할 신규 상품 링크를 탐색합니다...")
            next_url = None
            try:
                product_links_container_selector = "ul.carousel-list"
                link_elements = driver.find_elements(By.CSS_SELECTOR, f"{product_links_container_selector} a")

                for link_element in link_elements:
                    href = link_element.get_attribute('href')
                    if href:
                        full_url = urljoin(driver.current_url, href)
                        clean_url = full_url.split('?')[0]

                        if clean_url not in scraped_urls:
                            next_url = clean_url
                            print(f"다음 수집할 상품을 찾았습니다: {next_url}")
                            break  # 첫 번째 신규 링크를 찾으면 바로 탐색 종료

                if not next_url:
                    print("더 이상 수집할 새로운 상품이 없습니다. 작업을 종료합니다.")

            except Exception as e:
                print(f"다른 상품 링크를 찾는 중 오류가 발생했습니다: {e}")

            current_url = next_url  # 다음 루프를 위해 URL을 업데이트. None이면 루프 종료.
            time.sleep(2)

        if max_products is not None and products_scraped_count >= max_products:
            print(f"\n목표했던 {max_products}개의 상품 수집을 완료했습니다.")

    except KeyboardInterrupt:
        print("\n사용자에 의해 전체 수집이 중단되었습니다.")
    except Exception as e:
        print(f"전체 스크래핑 실행 중 심각한 오류 발생: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except OSError as e:
                print(f"드라이버 종료 중 OS 오류 발생 (무시 가능): {e}")
        print(f"\n모든 작업을 종료합니다. 최종 결과는 '{output_filename}' 파일을 확인하세요.")