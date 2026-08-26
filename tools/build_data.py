# -*- coding: utf-8 -*-
"""国土数値情報 A27（小学校区）+ P29（学校）+ 児童数から data/schools.js を生成する。

使い方:
  python3 build_data.py <A27のgeojson> <P29のgeojson>

A27-23（令和5年度）には以下の既知の誤り・古い情報があり、ここで補正する:
  - 吹田「弘済小学校」の校区 → 実際は古江台小学校の校区（住所が古江台小と一致）
  - 吹田「山田第五小学校」の校区が2件 → 片方（山田西1-4-1）は山田第三小学校の校区。
    さらに山田第五は2025年3月閉校・山田第三へ統合のため、両方を山田第三に合算
  - 豊中「庄内小学校」→ 2022年に庄内さくら学園（義務教育学校）へ統合。
    さくら学園は2024年から野田町1-1の新校舎
  - 豊中「庄内南・庄内西・千成」→ 2026年4月に庄内よつば学園（義務教育学校・千成町）へ統合
"""
import json, sys, os

CITIES = {'27203': '豊中市', '27205': '吹田市'}

YOMI_OVERRIDES = {
    '新田': 'しんでん', '新田南': 'しんでんみなみ', '豊島': 'てしま', '豊島北': 'てしまきた',
    '豊島西': 'てしまにし', '中豊島': 'なかてしま', '熊野田': 'くまのだ', '南丘': 'みなみおか',
    '東丘': 'ひがしおか', '北丘': 'きたおか', '泉丘': 'いずみおか', '東泉丘': 'ひがしいずみおか',
    '東豊台': 'ひがしとよだい', '東豊中': 'ひがしとよなか', '桜井谷': 'さくらいだに',
    '桜井谷東': 'さくらいだにひがし', '螢池': 'ほたるがいけ', '野畑': 'のばたけ',
    '佐竹台': 'さたけだい', '佐井寺': 'さいでら', '東佐井寺': 'ひがしさいでら',
    '東山田': 'ひがしやまだ', '西山田': 'にしやまだ', '古江台': 'ふるえだい',
    '山田第三': 'やまだだいさん', '庄内さくら学園': 'しょうないさくらがくえん',
    '庄内よつば学園': 'しょうないよつばがくえん',
}


def to_multi(geom):
    return geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]


def rnd(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 6), round(c[1], 6)]
    return [rnd(x) for x in c]


def main(a27_path, p29_path):
    here = os.path.dirname(os.path.abspath(__file__))
    a27 = json.load(open(a27_path))
    p29 = json.load(open(p29_path))
    students = json.load(open(os.path.join(here, 'students.json')))
    yomi_tsv = os.path.join(here, 'yomi.tsv')
    yomi = {}
    if os.path.exists(yomi_tsv):
        for line in open(yomi_tsv):
            k, v = line.rstrip('\n').split('\t')
            yomi[k] = v
    yomi.update(YOMI_OVERRIDES)

    points = {}
    for f in p29['features']:
        p = f['properties']
        if p['P29_001'] in CITIES and p['P29_003'] in ('16001', '16014'):
            points[p['P29_004']] = f['geometry']['coordinates']

    schools = {}  # name -> entry
    def add(name, geom, city, address, point=None):
        e = schools.get(name)
        if e is None:
            e = schools[name] = {
                'name': name, 'short': name.replace(city + '立', ''), 'city': city,
                'address': address, 'point': point or points.get(name),
                'polygon': {'type': 'MultiPolygon', 'coordinates': []},
            }
        if point:
            e['point'] = point
            e['address'] = address
        e['polygon']['coordinates'] += to_multi(geom)

    for f in a27['features']:
        p = f['properties']
        code = p['A27_001']
        if code not in CITIES:
            continue
        city = CITIES[code]
        name = p['A27_002'] + p['A27_004']
        addr = p['A27_005']
        geom = f['geometry']

        # --- A27の補正（docstring参照） ---
        if name == '吹田市立弘済小学校':
            add('吹田市立古江台小学校', geom, city, '吹田市古江台5-6-1')
        elif name == '吹田市立山田第五小学校':
            add('吹田市立山田第三小学校', geom, city, '吹田市山田西1-4-1')
        elif name == '豊中市立庄内小学校':
            add('豊中市立庄内さくら学園', geom, city, '豊中市野田町1-1',
                point=[135.473495, 34.753349])
        elif name == '豊中市立庄内さくら学園':
            add(name, geom, city, '豊中市野田町1-1', point=[135.473495, 34.753349])
        elif name in ('豊中市立庄内南小学校', '豊中市立庄内西小学校', '豊中市立千成小学校'):
            add('豊中市立庄内よつば学園', geom, city, '豊中市千成町2-2-65',
                point=[135.47321, 34.738225])
        else:
            add(name, geom, city, addr)

    st_all = {}
    st_all.update(students['suita']['schools'])
    st_all.update(students['toyonaka']['schools'])

    out = []
    for e in schools.values():
        assert e['point'], '位置不明: ' + e['name']
        assert e['name'] in st_all, '児童数不明: ' + e['name']
        base = e['short'].replace('小学校', '')
        e['yomi'] = yomi.get(base, '')
        e['students'] = st_all[e['name']]
        e['point'] = [round(e['point'][0], 6), round(e['point'][1], 6)]
        e['polygon']['coordinates'] = rnd(e['polygon']['coordinates'])
        out.append(e)

    missing = set(st_all) - set(schools)
    assert not missing, '校区が無い学校: %s' % missing
    out.sort(key=lambda e: (e['city'], e['yomi']))

    data = {
        'meta': {
            'boundarySource': '国土数値情報 小学校区データ（A27-23 令和5年度）国土交通省（統合・改称を2026年時点の情報に補正）',
            'pointSource': '国土数値情報 学校データ（P29-23 令和5年度）国土交通省',
            'suita': {k: students['suita'][k] for k in ('source', 'sourceUrl', 'asOf')},
            'toyonaka': {k: students['toyonaka'][k] for k in ('source', 'sourceUrl', 'asOf')},
        },
        'schools': out,
    }
    dst = os.path.join(here, '..', 'data', 'schools.js')
    with open(dst, 'w') as f:
        f.write('window.SCHOOL_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    n_su = sum(1 for e in out if e['city'] == '吹田市')
    n_to = sum(1 for e in out if e['city'] == '豊中市')
    print('生成完了: %d校（吹田%d / 豊中%d） %dKB' % (
        len(out), n_su, n_to, os.path.getsize(dst) // 1024))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
