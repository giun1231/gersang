from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    item = request.args.get("item")
    server = "청룡"

    # 거타 검색 URL 구성
    search_url = f"https://geota.co.kr/gersang/calculator/item?server={server}&item={item}"
    
    # 거타에서 검색 결과 가져오기 (크롤링은 실제 서비스 배포 시에는 API 방식 권장)
    try:
        response = requests.get(search_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        result = soup.find("div", {"class": "item-cost-container"})
        result_html = result.decode_contents() if result else "검색 결과를 찾을 수 없습니다."
    except Exception as e:
        result_html = f"오류 발생: {e}"

    return render_template("result.html", item=item, result=result_html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
