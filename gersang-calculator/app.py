
from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import urllib.parse

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
<body class="p-5">
  <h1 class="mb-4">일편단심 계산기</h1>
  <form method="post">
    <div class="mb-3 position-relative">
      <input type="text" id="item_name" name="item_name" class="form-control" placeholder="아이템 이름 입력 (예: 화룡도)" required autocomplete="off">
      <ul id="suggestions" class="list-group position-absolute w-100" style="z-index:1000;"></ul>
    </div>
    <button type="submit" class="btn btn-primary">계산하기</button>
  </form>
  {% if result %}
    <hr>
    <h3>{{ item_name }} 제작 비용</h3>
    <ul class="list-group">
      {% for entry in result['details'] %}
        <li class="list-group-item">
          {{ entry['name'] }} x {{ entry['qty'] }} → {{ entry['price'] | format_price }} × {{ entry['qty'] }} = {{ entry['subtotal'] | format_price }}냥
        </li>
      {% endfor %}
    </ul>
    <h4 class="mt-4">총 제작 비용: {{ result['total'] | format_price }}냥</h4>
  {% endif %}
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

def calculate_cost(item_name):
    recipe = get_recipe_from_gerniverse(item_name)
    if not recipe:
        return None

    prices = get_market_prices_from_geota()
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
    url = "https://www.gerniverse.app/item"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    suggestions = []

    for a in soup.select('a[href^="/item/"]'):
        name = a.text.strip()
        if query in name:
            suggestions.append(name)

    return jsonify(suggestions[:10])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)
