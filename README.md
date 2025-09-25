# 쿠팡 리뷰 수집기

쿠팡 상품의 리뷰를 자동으로 수집하여 CSV 파일로 저장하는 도구입니다.

## 필요 라이브러리

```bash
pip install undetected-chromedriver selenium beautifulsoup4 pandas
```

## 사용방법

### 1. 배치 처리

1. URL 목록 파일 생성 (예: `coupang_list.txt`)
2. Python 스크립트 실행:
```bash
python get_reviews.py coupang_list.txt
```

### 2. 단일 상품 처리
```bash
python get_reviews.py "https://www.coupang.com/vp/products/123456789"
```

### 3. 사용법 안내
```bash
python get_reviews.py
```

### 4. URL 목록 파일 형식 예제
파일명: `coupang_list.txt`
```
# 쿠팡 상품 URL 목록
# # 으로 시작하는 줄은 주석으로 무시됩니다

https://www.coupang.com/vp/products/123456789
https://www.coupang.com/vp/products/987654321
https://www.coupang.com/vp/products/456789123
```

## 출력 파일

- 파일명 형식: `Coupang_Reviews_{ProductID}_{타임스탬프}.csv`
- 컬럼: `ProductID`, `Date`, `Review`
- 인코딩: UTF-8 with BOM (Excel에서 한글 깨짐 방지)
