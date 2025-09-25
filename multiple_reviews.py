import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import csv
from datetime import datetime
from urllib.parse import urljoin


def get_quarter(month):
    """월(month)을 기반으로 분기를 계산합니다."""
    return (month - 1) // 3 + 1


def scrape_coupang_reviews_on_page(driver):
    """
    [로직 수정] 페이지 끝 감지 오류를 해결하고, 정렬 기능을 제거한 버전입니다.
    """
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
                print("마지막 페이지 그룹입니다. 수집을 종료합니다.")
                break

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"리뷰 수집 중 심각한 오류 발생: {e}")

    print(f"\n현재 상품에 대한 리뷰 {len(all_reviews_data)}개 수집 완료. 데이터를 저장합니다...")
    if not all_reviews_data:
        print("수집된 리뷰가 없어 저장할 파일이 없습니다.")
        return

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
        product_title = driver.title.split(' - ')[0].replace('/', '_').replace('\\', '_')
        filename = f"Coupang_{product_title}_{quarter_key}.csv"
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Review'])
            for review in reviews:
                writer.writerow([review['date'], review['content']])
        print(f"'{filename}' 파일에 {len(reviews)}개의 리뷰를 저장했습니다.")


if __name__ == "__main__":
    start_url = input("리뷰를 수집할 첫 번째 쿠팡 제품의 전체 URL을 입력하세요: ")

    ## [추가] 최대 수집 상품 개수를 질문합니다.
    max_products = None
    try:
        max_products_input = input("수집할 최대 상품 개수를 입력하세요 (전체 수집은 그냥 Enter): ")
        if max_products_input:
            max_products = int(max_products_input)
    except ValueError:
        print("잘못된 입력입니다. 전체 상품을 수집합니다.")
        max_products = None

    ## [수정] URL에서 파라미터를 제거한 순수 URL로 중복을 관리합니다.
    start_url_clean = start_url.split('?')[0]
    urls_to_scrape = [start_url_clean]
    scraped_urls = set()
    driver = None
    products_scraped_count = 0  # 수집한 상품 개수를 셉니다.

    try:
        options = uc.ChromeOptions()
        options.add_argument('--blink-settings=imagesEnabled=false')
        driver = uc.Chrome(options=options, use_subprocess=True)

        ## [수정] 최대 수집 개수에 도달하면 루프를 멈추도록 조건을 추가합니다.
        while urls_to_scrape and (max_products is None or products_scraped_count < max_products):
            current_url = urls_to_scrape.pop(0)
            if not current_url or current_url in scraped_urls:
                continue

            if "coupang.com" not in current_url:
                print(f"유효한 쿠팡 URL이 아닙니다: {current_url}")
                continue

            scraped_urls.add(current_url)
            products_scraped_count += 1
            print(
                f"\n{'=' * 50}\n[ {products_scraped_count} / {max_products if max_products else '∞'} 번째 상품 리뷰 수집 시작 ]\nURL: {current_url}\n{'=' * 50}")

            driver.get(current_url)
            time.sleep(1)

            scrape_coupang_reviews_on_page(driver)

            print("\n현재 페이지에서 다른 상품 링크를 탐색합니다...")
            try:
                # ===================================================================================
                # ## [수정] 보내주신 HTML을 기반으로 CSS 선택자를 'ul.carousel-list'로 확정했습니다. ##
                # ===================================================================================

                product_links_container_selector = "ul.carousel-list"

                link_elements = driver.find_elements(By.CSS_SELECTOR, f"{product_links_container_selector} a")

                new_links_found = 0
                for link_element in link_elements:
                    href = link_element.get_attribute('href')
                    if href:
                        full_url = urljoin(driver.current_url, href)

                        ## [수정] URL에서 파라미터를 제거하여 순수 상품 링크로 만듭니다.
                        clean_url = full_url.split('?')[0]

                        if clean_url not in scraped_urls and clean_url not in urls_to_scrape:
                            urls_to_scrape.append(clean_url)
                            new_links_found += 1

                if new_links_found > 0:
                    print(f"새로운 상품 링크 {new_links_found}개를 발견하여 대기열에 추가했습니다.")
                else:
                    print("탐색 영역에서 새로운 상품 링크를 찾지 못했습니다.")

            except Exception as e:
                print(f"다른 상품 링크를 찾는 중 오류가 발생했습니다: {e}")

            print(f"현재까지 {len(scraped_urls)}개 상품 수집 완료. 대기열에 {len(urls_to_scrape)}개 상품이 남았습니다.")
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
        print("\n모든 작업을 종료합니다.")