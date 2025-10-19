# ライブラリ使用例

## 主要ライブラリの実装例

### 1. pandas（CSV解析）
```python
import pandas as pd
import chardet

# Shift_JIS文字コード検出
with open('meisai202510.csv', 'rb') as f:
    encoding = chardet.detect(f.read())['encoding']

# CSV読み込み
df = pd.read_csv('meisai202510.csv', encoding=encoding)

# YYMMDD形式を変換
df['利用日'] = pd.to_datetime(df['利用日'], format='%y%m%d')

# 月別集計
monthly = df.groupby(df['利用日'].dt.month)['金額'].sum()
```

### 2. gspread（Google Sheets連携）
```python
import gspread
from google.oauth2.service_account import Credentials

# サービスアカウント認証
scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    'config/service_account.json', 
    scopes=scopes
)
client = gspread.authorize(creds)

# スプレッドシート取得
sheet = client.open_by_key('SPREADSHEET_ID')
worksheet = sheet.worksheet('2025年')

# セル更新（B11セルに加算）
current_value = worksheet.acell('B11').value
new_value = int(current_value) + 5780
worksheet.update_acell('B11', new_value)
```

### 3. Flask（Webアプリケーション）
```python
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['csv_file']
    df = pd.read_csv(file, encoding='shift_jis')
    
    # 処理実行
    result = process_csv(df)
    
    return render_template('result.html', result=result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### 4. chardet（文字コード検出）
```python
import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']  # 'shift_jis'

# 使用例
encoding = detect_encoding('meisai202510.csv')
df = pd.read_csv('meisai202510.csv', encoding=encoding)
```

## ライブラリ間の連携フロー

```
1. Flask → リクエスト受信
2. chardet → 文字コード検出
3. pandas → CSV解析・データ変換
4. gspread → Google Sheets更新
5. Jinja2 → 結果画面レンダリング
```