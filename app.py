
from flask import Flask, request, redirect, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('', 'index.html')

@app.route('/search')
def search():
    query = request.args.get('query', '')
    if query:
        return redirect(f'https://geota.co.kr/#!/search/{query}')
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
