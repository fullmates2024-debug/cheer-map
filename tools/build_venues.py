# -*- coding: utf-8 -*-
"""レッスン会場＋保育・幼児施設のデータを data/*.js に生成する。

入力（tools/src/）:
  venues.json    … チア会場ナビ（Documents/チアクラブ事業/事業計画/_work/会場空き状況サイト）
                   の会場92件。市・施設名・住所・緯度経度・A/B枠数・予約システム・警告
  preschools.csv … 同プロジェクトで整備した保育園・幼稚園・認定こども園・小規模保育563件
                   （ここdeサーチ＋市公式補正・2026-09-09時点）
出力: data/venues.js, data/preschools.js

会場の空き枠（a=A枠数: 平日16-18時を含む同一室同一曜日4週以上連続の空き）は取得日時点の
スナップショット。更新時は会場ナビ側を再取得してから venues.json を作り直すこと。
"""
import csv, json, os

here = os.path.dirname(os.path.abspath(__file__))

src = json.load(open(os.path.join(here, 'src', 'venues.json'), encoding='utf-8'))
for v in src['venues']:
    v['lat'] = round(float(v['lat']), 6)
    v['lon'] = round(float(v['lon']), 6)
dst = os.path.join(here, '..', 'data', 'venues.js')
with open(dst, 'w') as f:
    f.write('window.VENUE_DATA = ' + json.dumps(src, ensure_ascii=False) + ';\n')
print('venues.js: %d件 %dKB' % (len(src['venues']), os.path.getsize(dst) // 1024))

items = []
with open(os.path.join(here, 'src', 'preschools.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if not r.get('lat'):
            continue
        items.append({'c': r['city'], 't': r['type'], 'n': r['name'],
                      'lat': round(float(r['lat']), 6), 'lon': round(float(r['lon']), 6)})
data = {'asOf': '2026-09-09時点（こども家庭庁ここdeサーチ＋各市公式で閉園・新設を補正）',
        'items': items}
dst = os.path.join(here, '..', 'data', 'preschools.js')
with open(dst, 'w') as f:
    f.write('window.PRESCHOOL_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
from collections import Counter
print('preschools.js: %d件 %s %dKB' % (
    len(items), dict(Counter(i['t'] for i in items)), os.path.getsize(dst) // 1024))
