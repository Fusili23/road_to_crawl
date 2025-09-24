import requests
from bs4 import BeautifulSoup
import csv
import time

print("--- 네이버 뉴스 IT/과학 헤드라인 크롤링 ---")

# 1. 요청(Request) 단계
# ----------------------------------------------------------------
url = "https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=105"  # IT/과학 섹션

headers = {
    "User-Agent": "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
}

print(f"목표 URL: {url}")
response = requests.get(url, headers=headers)
all_headlines = []

# 2. 파싱(Parsing) 및 추출(Extraction) 단계
# ----------------------------------------------------------------
if response.status_code == 200:
    print("✅ 서버로부터 HTML을 성공적으로 가져왔습니다.")

    soup = BeautifulSoup(response.text, 'lxml')

    # HTML 분석 결과, 헤드라인 제목과 링크는 class가 'sa_text_title'인 <a> 태그 안에 포함되어 있음
    # 이 태그를 모두 찾아서 반복 처리
    headline_tags = soup.find_all('a', class_='sa_text_title')

    print(f"\n--- 총 {len(headline_tags)}개의 헤드라인 추출을 시작합니다. ---")

    for tag in headline_tags:
        # 태그에서 텍스트(제목)와 href 속성(링크)을 추출
        # get_text(strip=True)는 태그 안의 텍스트에서 양쪽 공백을 제거해줌
        title = tag.get_text(strip=True)
        link = tag.get('href')

        # 추출한 데이터를 딕셔너리 형태로 리스트에 추가
        all_headlines.append({
            "제목": title,
            "링크": link
        })
        print(f"추출 완료: {title}")

else:
    print(f"❌ 오류: 서버 응답에 실패했습니다. (응답 코드: {response.status_code})")

# 3. 저장(Storage) 단계
# ----------------------------------------------------------------
if all_headlines:
    CSV_FILENAME = "naver_it_news.csv"
    fieldnames = ["제목", "링크"]

    print(f"\n--- 추출한 헤드라인을 '{CSV_FILENAME}' 파일로 저장합니다. ---")

    # 'w' 모드로 파일을 열고, 한글 깨짐 방지를 위해 encoding='utf-8-sig' 사용
    with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # CSV 파일에 헤더(제목, 링크)를 씀
        writer.writeheader()

        # 리스트에 담긴 모든 헤드라인 데이터를 파일에 씀
        writer.writerows(all_headlines)

    print(f"✅ 파일 저장이 완료되었습니다.")
else:
    print("⚠️ HTML은 가져왔으나, 추출할 헤드라인을 찾지 못했습니다.")

