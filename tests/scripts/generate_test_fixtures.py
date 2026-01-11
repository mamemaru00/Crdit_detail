"""テストファイルのエンコーディング変換スクリプト"""

# valid_shiftjis.csvをShift_JISでエンコード
content_sjis = """ご利用明細書,,,,,,,,,
,,,,,,,,
2025年01月ご請求分,,,,,,,,,
,,,,,,,,
ご請求金額,,,,,,,,,
15280円,,,,,,,,,
,,,,,,,,
利用日,利用者,利用先,支払方法,利用額,手数料,支払額,備考,
250115,本人,イオンスタイル,１回,,,5280,,
250116,本人,セブンイレブン,１回,,,1200,,
250118,家族,ファミリーマート,１回,,,850,,
250120,本人,スターバックス,１回,,,480,Apple Pay利用分
250125,本人,Amazonマーケットプレイス,１回,,,7470,,
"""

with open('tests/fixtures/csv/valid_shiftjis.csv', 'w', encoding='shift_jis') as f:
    f.write(content_sjis)

print('valid_shiftjis.csv encoded as Shift_JIS')

# 大容量ファイルの生成
output_path = 'tests/fixtures/csv/large_file.csv'

with open(output_path, 'w', encoding='utf-8') as f:
    # ヘッダー部分
    f.write('ご利用明細書,,,,,,,,,\n')
    f.write(',,,,,,,,\n')
    f.write('2025年01月ご請求分,,,,,,,,,\n')
    f.write(',,,,,,,,\n')
    f.write('ご請求金額,,,,,,,,,\n')
    f.write('10000000円,,,,,,,,,\n')
    f.write(',,,,,,,,\n')
    f.write('利用日,利用者,利用先,支払方法,利用額,手数料,支払額,備考,\n')

    # 明細データを大量に生成（約5000行で10MB程度）
    for i in range(5000):
        date = f'25{(i % 12 + 1):02d}{(i % 28 + 1):02d}'
        user = '本人' if i % 2 == 0 else '家族'
        store = f'テスト店舗{i:04d}'
        amount = (i * 100) % 100000
        f.write(f'{date},{user},{store},１回,,,{amount},,\n')

import os
size_mb = os.path.getsize(output_path) / (1024 * 1024)
print(f'Generated large_file.csv: {size_mb:.2f} MB')
