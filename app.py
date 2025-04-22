from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import json
import csv
import threading
import time

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>일편단심 계산기</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body class="p-5 bg-light">
  <div class="container">
    <h1 class="mb-4 text-primary">일편단심 제작 비용 계산기</h1>
    <form method="post" class="mb-4">
      <div class="mb-3 position-relative">
        <input type="text" id="item_name" name="item_name" class="form-control" placeholder="아이템 이름 입력 (예: 화룡도)" required autocomplete="off">
        <ul id="suggestions" class="list-group position-absolute w-100" style="z-index:1000;"></ul>
      </div>
      <button type="submit" class="btn btn-success w-100">💰 제작 비용 계산</button>
    </form>
    {% if result %}
      <div class="card shadow-sm">
        <div class="card-header bg-primary text-white">
          <h5 class="mb-0">{{ item_name }} 제작 비용</h5>
        </div>
        <div class="card-body">
          <table class="table table-bordered text-center">
            <thead class="table-light">
              <tr>
                <th>재료명</th>
                <th>수량</th>
                <th>단가</th>
                <th>합계</th>
              </tr>
            </thead>
            <tbody>
              {% for entry in result['details'] %}
              <tr>
                <td>{{ entry['name'] }}</td>
                <td>{{ entry['qty'] }}</td>
                <td>{{ entry['price'] | format_price }}</td>
                <td>{{ entry['subtotal'] | format_price }}냥</td>
              </tr>
              {% endfor %}
            </tbody>
            <tfoot>
              <tr class="table-warning">
                <th colspan="3">총 제작 비용</th>
                <th>{{ result['total'] | format_price }}냥</th>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    {% endif %}
  </div>

  <script>
    $('#item_name').on('input', function() {
      const query = $(this).val();
      if (query.length < 2) {
        $('#suggestions').empty();
        return;
      }
      $.get('/suggest', { q: query }, function(data) {
        let list = '';
        data.forEach(function(item) {
          list += '<li class="list-group-item list-group-item-action">' + item + '</li>';
        });
        $('#suggestions').html(list);
      });
    });

    $(document).on('click', '#suggestions li', function() {
      $('#item_name').val($(this).text());
      $('#suggestions').empty();
    });
  </script>
</body>
</html>
"""

def format_price(value):
    return f"{value:,}"

@app.template_filter('format_price')
def format_price_filter(value):
    return format_price(value)

def get_recipe_from_gerniverse(item_name):
    encoded_name = urllib.parse.quote(item_name)
    url = f"https://www.gerniverse.app/item/{encoded_name}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    recipe = {}
    material_section = soup.find('div', class_='item-material')
    if not material_section:
        return recipe

    for li in material_section.find_all('li'):
        parts = li.text.strip().rsplit('x', 1)
        if len(parts) == 2:
            name = parts[0].strip()
            try:
                qty = int(parts[1].strip())
                recipe[name] = qty
            except:
                continue

    return recipe

def get_market_prices_from_geota():
    url = "https://geota.co.kr/gersang/yukeuijeon?serverId=4"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    market = {}

    rows = soup.select("table tbody tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            try:
                name = cols[0].text.strip()
                price = cols[2].text.strip().replace(",", "").replace("냥", "")
                market[name] = int(price)
            except:
                continue
    return market

def save_prices_to_csv(prices):
    with open("prices.csv", "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["아이템명", "가격"])
        for name, price in prices.items():
            writer.writerow([name, price])

def calculate_cost(item_name):
    recipe = get_recipe_from_gerniverse(item_name)
    if not recipe:
        return None

    prices = get_market_prices_from_geota()
    save_prices_to_csv(prices)

    details = []
    total = 0

    for name, qty in recipe.items():
        price = prices.get(name, 0)
        subtotal = price * qty
        total += subtotal
        details.append({
            'name': name,
            'qty': qty,
            'price': price,
            'subtotal': subtotal
        })
    return {'details': details, 'total': total}

ALL_ITEMS = set()
CATEGORIES = ['sword', 'twin', 'spear', 'axe', 'bow', 'crossbow', 'gun', 'wand', 'staff', 'accessory', 'armor', 'helmet', 'ring', 'shield', 'shoes', 'bracelet', 'glove', 'scroll']

def load_all_items():
    for category in CATEGORIES:
        url = f"https://www.gerniverse.app/item?category={category}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a in soup.select('a[href^="/item/"]'):
            name = a.text.strip()
            if name:
                ALL_ITEMS.add(name)
    with open("items.csv", "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["아이템명"])
        for item in sorted(ALL_ITEMS):
            writer.writerow([item])

def schedule_price_update():
    def run():
        while True:
            prices = get_market_prices_from_geota()
            save_prices_to_csv(prices)
            time.sleep(3 * 24 * 60 * 60)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

load_all_items()
schedule_price_update()

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    item_name = ""
    if request.method == 'POST':
        item_name = request.form['item_name']
        result = calculate_cost(item_name)
    return render_template_string(HTML_TEMPLATE, result=result, item_name=item_name)

@app.route('/suggest')
def suggest():
    query = request.args.get('q', '').strip()
    matched = [name for name in ALL_ITEMS if query in name]
    return jsonify(matched[:10])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)
