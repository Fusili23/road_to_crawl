import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException


def scrape_all_coupang_reviews_final(url):
    """
    정확한 선택자를 사용하여 주어진 쿠팡 URL의 모든 리뷰를 수집합니다.
    """
    all_reviews = []

    try:
        options = uc.ChromeOptions()
        # options.add_argument('--headless')
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.get(url)
        # 웹 드라이버가 요소를 찾을 때까지 최대 10초간 기다리도록 설정
        wait = WebDriverWait(driver, 10)

    except Exception as e:
        print(f"드라이버 설정 중 오류 발생: {e}")
        return

    # [수정됨] ID를 기반으로 상품평 탭을 찾아 클릭합니다.
    try:
        # '상품평' 탭(링크)이 클릭 가능해질 때까지 기다립니다.
        review_tab_link = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#sdpReview']"))
        )
        driver.execute_script("arguments[0].click();", review_tab_link)
        # 리뷰 섹션이 로드될 시간을 줍니다.
        time.sleep(3)
    except TimeoutException:
        print("상품평 탭을 찾지 못했습니다. 타임아웃이 발생했습니다.")
        driver.quit()
        return
    except Exception as e:
        print(f"상품평 탭 클릭 중 오류 발생: {e}")
        driver.quit()
        return

    page = 1
    while True:
        print(f"{page}페이지 리뷰를 수집 중입니다...")

        try:
            # 리뷰 컨테이너가 화면에 나타날 때까지 기다립니다.
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sdp-review__article__list")))

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            review_contents = soup.find_all('div', class_='sdp-review__article__list__review__content')

            if not review_contents and page == 1:
                print("페이지에서 리뷰를 찾을 수 없습니다.")
                break

            for content in review_contents:
                all_reviews.append(content.get_text(strip=True))

            # 다음 페이지 버튼 찾기 (비활성화되지 않은 버튼)
            next_button = driver.find_element(By.CSS_SELECTOR, 'button.sdp-review__article__page__next:not([disabled])')
            driver.execute_script("arguments[0].click();", next_button)
            page += 1
            # 페이지 전환 후 다음 리뷰 목록이 로드될 때까지 잠시 기다립니다.
            time.sleep(2)

        except NoSuchElementException:
            print("마지막 페이지입니다. 수집을 종료합니다.")
            break
        except TimeoutException:
            print("리뷰를 로드하는 중 타임아웃이 발생했습니다. 수집을 종료합니다.")
            break
        except Exception as e:
            print(f"수집 중 오류 발생: {e}")
            break

    driver.quit()

    if all_reviews:
        with open('coupang_all_reviews_final.txt', 'w', encoding='utf-8') as f:
            for i, review in enumerate(all_reviews, 1):
                f.write(f"--- 리뷰 {i} ---\n{review}\n\n")
        print(f"총 {len(all_reviews)}개의 리뷰를 'coupang_all_reviews_final.txt' 파일에 저장했습니다.")
    else:
        print("수집된 리뷰가 없습니다.")


if __name__ == "__main__":
    product_url = input("리뷰를 수집할 쿠팡 제품의 전체 URL을 입력하세요: ")
    if "coupang.com" in product_url:
        scrape_all_coupang_reviews_final(product_url)
    else:
        print("유효한 쿠팡 URL이 아닙니다.")