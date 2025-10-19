# Flaskアプリケーション構成

## 6.1 ディレクトリ構成

```
project_root/
├── app.py                 # メインアプリケーション
├── config.py              # 設定ファイル
├── requirements.txt       # 依存パッケージ
├── credentials.json       # Google API認証情報
├── static/
│   ├── css/
│   │   └── style.css     # カスタムCSS
│   └── js/
│       ├── main.js       # メイン画面用JS
│       └── mapping.js    # マッピング管理用JS
├── templates/
│   ├── base.html         # ベーステンプレート
│   ├── index.html        # メイン画面
│   ├── mapping.html      # マッピング管理画面
│   └── unregistered.html # 未登録店舗確認画面
└── modules/
    ├── csv_processor.py  # CSV処理モジュール
    ├── sheets_api.py     # Sheets API連携
    ├── mapping_manager.py # マッピング管理
    └── category_logic.py  # カテゴリ振り分けロジック
```

## 6.2 主要ルート定義

- `/` - メイン画面
- `/mapping` - マッピング管理画面
- `/api/upload` - CSVアップロード処理
- `/api/preview` - CSVプレビュー取得
- `/api/execute` - スプレッドシート取込実行
- `/api/mappings` - マッピングCRUD操作
- `/api/unregistered` - 未登録店舗処理

## 6.3 使用技術スタック

- Flask 3.0+
- google-api-python-client
- pandas（CSV処理）
- Bootstrap 5.3
- Jinja2テンプレート