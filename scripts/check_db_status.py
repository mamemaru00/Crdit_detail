"""SQLiteデータベースの状態確認スクリプト"""
import sqlite3
from pathlib import Path

db_path = Path('C:/work/Lesson/個人開発/Crdit_detail/data/mappings.db')

if not db_path.exists():
    print("データベースファイルが存在しません")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # テーブル一覧
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"テーブル一覧: {tables}")

    # レコード数
    cursor.execute("SELECT COUNT(*) FROM store_mappings")
    total = cursor.fetchone()[0]
    print(f"\n総レコード数: {total}件")

    # サンプルレコード
    cursor.execute("SELECT id, pattern, category, column_name, priority, source FROM store_mappings LIMIT 10")
    print("\nサンプルレコード:")
    for row in cursor.fetchall():
        print(f"  ID={row[0]}, pattern={row[1]}, category={row[2]}, column={row[3]}, priority={row[4]}, source={row[5]}")

    conn.close()
