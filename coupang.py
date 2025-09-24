from bs4 import BeautifulSoup


def parse_reviews_from_file(file_path):
    """
    주어진 HTML 파일 경로에서 모든 리뷰 정보를 파싱하여 텍스트 파일로 저장합니다.
    """
    try:
        # 로컬 HTML 파일을 UTF-8 인코딩으로 엽니다.
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_content, 'html.parser')

    # 모든 리뷰 article 태그를 찾습니다.
    # 각 리뷰는 'sdp-review__article__list' 클래스를 가진 article 태그에 담겨 있습니다.
    articles = soup.find_all('article', class_='sdp-review__article__list')

    if not articles:
        print("HTML 파일에서 리뷰를 찾을 수 없습니다. 클래스 이름이 변경되었을 수 있습니다.")
        return

    all_reviews_data = []

    for article in articles:
        # 각 리뷰(article) 내에서 원하는 정보를 추출합니다.

        # 1. 작성자
        user_name_element = article.find('span', class_='sdp-review__article__list__info__user__name')
        user_name = user_name_element.get_text(strip=True) if user_name_element else "작성자 없음"

        # 2. 작성일
        date_element = article.find('div', class_='sdp-review__article__list__info__product-info__reg-date')
        review_date = date_element.get_text(strip=True) if date_element else "날짜 없음"

        # 3. 리뷰 제목 (Headline)
        headline_element = article.find('div', class_='sdp-review__article__list__headline')
        headline = headline_element.get_text(strip=True) if headline_element else "제목 없음"

        # 4. 리뷰 본문
        content_element = article.find('div', class_='sdp-review__article__list__review__content')
        content = content_element.get_text(strip=True).replace('<br>', '\n') if content_element else "내용 없음"

        # 추출한 정보를 딕셔너리 형태로 저장
        review_data = {
            'user': user_name,
            'date': review_date,
            'headline': headline,
            'content': content
        }
        all_reviews_data.append(review_data)

    # 수집된 리뷰를 파일로 저장
    if all_reviews_data:
        with open('coupang_reviews_from_file.txt', 'w', encoding='utf-8') as f:
            for i, review in enumerate(all_reviews_data, 1):
                f.write(f"--- 리뷰 {i} ---\n")
                f.write(f"작성자: {review['user']}\n")
                f.write(f"작성일: {review['date']}\n")
                f.write(f"제목: {review['headline']}\n")
                f.write("----------------\n")
                f.write(f"{review['content']}\n\n")
        print(f"총 {len(all_reviews_data)}개의 리뷰를 'coupang_reviews_from_file.txt' 파일에 저장했습니다.")
    else:
        print("수집된 리뷰가 없습니다.")


if __name__ == "__main__":
    file_name = 'element html.txt'  # 분석할 HTML 파일 이름
    parse_reviews_from_file(file_name)