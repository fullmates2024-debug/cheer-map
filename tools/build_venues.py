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

# 私立・国立小（校区なし・data/private_schools.js）
pv = []
with open(os.path.join(here, 'src', 'private_elem.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        pv.append({'city': r['city'], 'name': r['name'], 'kind': r['kind'],
                   'students': int(r['students']) if r['students'] else None,
                   'asOf': r['asof'],
                   'lat': round(float(r['lat']), 6), 'lon': round(float(r['lon']), 6)})
dst = os.path.join(here, '..', 'data', 'private_schools.js')
with open(dst, 'w') as f:
    f.write('window.PRIVATE_ELEM = ' + json.dumps(
        {'asOf': '2026-05-01時点（各校公式）', 'items': pv}, ensure_ascii=False) + ';\n')
print('private_schools.js: %d校' % len(pv))

# 園の定員・在籍（tools/src/capacity/*.csv: city,type,name,capacity,cap3plus,enrolled,asof,src）
capmap = {}
capdir = os.path.join(here, 'src', 'capacity')
if os.path.isdir(capdir):
    for fn in sorted(os.listdir(capdir)):
        if fn.endswith('.csv'):
            with open(os.path.join(capdir, fn), encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    capmap[(r['city'], r['type'], r['name'])] = r

def iv(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None

# 調査で判明した閉園・休止（2026-09-10 定員調査エージェントのnotes参照）
CLOSED = {('池田市', '保育園', '石橋保育所')}   # 令和6年4月閉園（跡地=みつはこども園）
SUSPENDED = {  # 休止中＝児童ゼロとして扱う（ピンは残し「休止中」表示）
 ('豊中市', '保育園', 'アイグラン保育園千里中央'),
 ('豊中市', '保育園', 'アイグラン保育園寺内'),
 ('豊中市', '保育園', 'アイグラン保育園西泉丘'),
 ('豊中市', '保育園', '聖愛クロス保育園 宮山町'),
}

items = []
matched = 0
with open(os.path.join(here, 'src', 'preschools.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if not r.get('lat'):
            continue
        k = (r['city'], r['type'], r['name'])
        if k in CLOSED:
            continue
        it = {'c': r['city'], 't': r['type'], 'n': r['name'],
              'lat': round(float(r['lat']), 6), 'lon': round(float(r['lon']), 6)}
        if k in SUSPENDED:
            it['sus'] = 1
        c = capmap.get(k)
        if c:
            it['cap'] = iv(c.get('capacity'))
            it['c3'] = iv(c.get('cap3plus'))
            it['enr'] = iv(c.get('enrolled'))
            if it['cap'] is not None or it['enr'] is not None:
                matched += 1
        if k in SUSPENDED:
            it['enr'] = 0   # 休止中＝在籍ゼロ（定員は参考として残す）
        items.append(it)
if capmap:
    print('定員データ: %d/%d園に人数あり（capmap %d行）' % (matched, len(items), len(capmap)))
    unk = [k for k in capmap if k not in {(i['c'], i['t'], i['n']) for i in items} and k not in CLOSED]
    if unk:
        print('!! preschools.csvと名前が一致しない行:', len(unk), unk[:5])
data = {'asOf': '2026-09-09時点（こども家庭庁ここdeサーチ＋各市公式で閉園・新設を補正）',
        'items': items}
dst = os.path.join(here, '..', 'data', 'preschools.js')
with open(dst, 'w') as f:
    f.write('window.PRESCHOOL_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
from collections import Counter
print('preschools.js: %d件 %s %dKB' % (
    len(items), dict(Counter(i['t'] for i in items)), os.path.getsize(dst) // 1024))
