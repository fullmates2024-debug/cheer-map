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
  - 高槻「芝生小学校」の校区が2件 → 学校コードB127210005291（芝生町3-16-2）は
    実際は丸橋小学校の校区（P29の学校コードで突合し確認・2026-09-10）

2026-09-10: 会場マップ対応で高槻・池田・茨木・島本を追加。
2026-10-12: 枚方・箕面・摂津・大阪市東淀川区・尼崎・西宮・伊丹・宝塚・川西を追加。
  - 引数は複数geojson可（大阪府と兵庫県のA27/P29を全部渡す。種別は中身で自動判別）
  - 大阪市はA27に校区ポリゴンが存在しない（市が未提供・PDF表のみ公開）ため、
    東淀川区はP29の学校位置のみで登録し polygon=None とする
  - 西宮の「上ヶ原/上ケ原」表記揺れはヶ/ケ正規化で突合。
    「西宮浜義務教育学校」はP29では「総合教育センター付属西宮浜義務教育学校」
  - 箕面の彩都の丘・止々呂美はA27/P29では法律上の小学校名 → 通称の
    「彩都の丘学園」「とどろみの森学園」に改称して登録（児童数は1〜6年の計）
  - 摂津「鳥飼東小学校」→ 2026年4月に鳥飼小学校へ統合のため校区を鳥飼小に合算
  - 枚方「禁野小学校」（2022年開校）はA27に校区が無いためP29の位置のみで登録
"""
import json, sys, os

CITIES = {'27203': '豊中市', '27204': '池田市', '27205': '吹田市',
          '27207': '高槻市', '27211': '茨木市', '27301': '島本町',
          '27210': '枚方市', '27220': '箕面市', '27224': '摂津市',
          '27114': '大阪市東淀川区',
          '28202': '尼崎市', '28204': '西宮市', '28207': '伊丹市',
          '28214': '宝塚市', '28217': '川西市'}
# A27に校区が無く、P29の学校位置のみで登録する市区（polygon=None になる）
POINT_ONLY = {'27114'}
# students.json のキー（この節がある市町は児童数を検証しランキング対象になる）
CITY_KEYS = {'吹田市': 'suita', '豊中市': 'toyonaka', '高槻市': 'takatsuki',
             '池田市': 'ikeda', '茨木市': 'ibaraki', '島本町': 'shimamoto',
             '枚方市': 'hirakata', '箕面市': 'minoh', '摂津市': 'settsu',
             '大阪市東淀川区': 'higashiyodogawa',
             '尼崎市': 'amagasaki', '西宮市': 'nishinomiya', '伊丹市': 'itami',
             '宝塚市': 'takarazuka', '川西市': 'kawanishi'}

def norm_ke(s):
    return s.replace('ケ', 'ヶ')

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
    # 2026-10-12 追加9市区＋高槻・池田・茨木（形態素解析の誤読を地名の正読で上書き）
    '昆陽里': 'こやのさと', '大桐': 'だいどう', '豊新': 'ほうしん',
    '仁川': 'にがわ', '良元': 'りょうげん', '小浜': 'こはま', '長尾台': 'ながおだい',
    '逆瀬台': 'さかせだい', '安倉': 'あくら', '安倉北': 'あくらきた', '末成': 'すえなり',
    '美座': 'みざ', '高司': 'たかつかさ', 'すみれガ丘': 'すみれがおか',
    '難波': 'なにわ', '難波の梅': 'なにわのうめ', '金楽寺': 'きんらくじ',
    '園田東': 'そのだひがし', '七松': 'ななまつ', '成徳': 'せいとく',
    '武庫庄': 'むこのしょう', '園和北': 'えんわきた', '潮': 'うしお',
    '下坂部': 'しもさかべ', '上坂部': 'かみさかべ', '明城': 'めいじょう',
    '多田東': 'ただひがし', '清和台南': 'せいわだいみなみ',
    '味舌': 'ました', '味生': 'みしょう', '別府': 'べふ', '千里丘': 'せんりおか',
    '樟葉': 'くずは', '樟葉南': 'くずはみなみ', '樟葉西': 'くずはにし', '樟葉北': 'くずはきた',
    '香里': 'こうり', '東香里': 'ひがしこうり', '香陽': 'こうよう', '春日': 'かすが',
    '氷室': 'ひむろ', '菅原東': 'すがわらひがし', '山田東': 'やまだひがし',
    'さだ東': 'さだひがし', '磯島': 'いそしま', '中宮': 'なかみや',
    '萱野東': 'かやのひがし',
    '呉服': 'くれは', '北豊島': 'きたてしま', '神田': 'こうだ',
    '春日丘': 'かすがおか', '清溪': 'きよたに', '忍頂寺': 'にんちょうじ',
    '耳原': 'みのはら', '沢池': 'さわいけ', '郡': 'こおり', '葦原': 'あしはら',
    '中条': 'ちゅうじょう', '庄栄': 'しょうえい',
    '阿武野': 'あぶの', '富田': 'とんだ', '三箇牧': 'さんがまき', '桃園': 'ももぞの',
    '五百住': 'よすみ', '土室': 'はむろ', '郡家': 'ぐんげ', '津之江': 'つのえ',
    '冠': 'かんむり', '柱本': 'はしらもと', '北大冠': 'きたおおかんむり',
    '芝生': 'しぼ', '樫田': 'かしだ', '真上': 'まかみ', '南平台': 'みなみへいだい',
    '安岡寺': 'あんこうじ',
    '瓦木': 'かわらぎ', '津門': 'つと', '用海': 'ようがい', '生瀬': 'なまぜ',
    '春風': 'はるかぜ', '西宮浜義務教育学校': 'にしのみやはま',
}


def to_multi(geom):
    return geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]


def rnd(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 6), round(c[1], 6)]
    return [rnd(x) for x in c]


def main(*paths):
    here = os.path.dirname(os.path.abspath(__file__))
    a27_feats, p29_feats = [], []
    for path in paths:
        d = json.load(open(path))
        if 'A27_001' in d['features'][0]['properties']:
            a27_feats += d['features']
        else:
            p29_feats += d['features']
    a27 = {'features': a27_feats}
    p29 = {'features': p29_feats}
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
            points.setdefault(norm_ke(p['P29_004']), f['geometry']['coordinates'])
    # P29の正式名が長い学校の別名
    if '西宮市立総合教育センター付属西宮浜義務教育学校' in points:
        points['西宮市立西宮浜義務教育学校'] = points['西宮市立総合教育センター付属西宮浜義務教育学校']

    schools = {}  # name -> entry
    def add(name, geom, city, address, point=None):
        e = schools.get(name)
        if e is None:
            owner = '大阪市立' if city == '大阪市東淀川区' else city + '立'
            e = schools[name] = {
                'name': name, 'short': name.replace(owner, ''), 'city': city,
                'address': address,
                'point': point or points.get(name) or points.get(norm_ke(name)),
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
        if name == '高槻市立芝生小学校' and p['A27_003'] == 'B127210005291':
            add('高槻市立丸橋小学校', geom, city, '高槻市芝生町3-16-2')
        elif name == '吹田市立弘済小学校':
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
        elif name == '摂津市立鳥飼東小学校':
            add('摂津市立鳥飼小学校', geom, city, '摂津市鳥飼下1-7-1')
        elif name == '箕面市立彩都の丘小学校':
            add('箕面市立彩都の丘学園', geom, city, '箕面市彩都粟生北2-1-5',
                point=[135.511095, 34.85708])
        elif name == '箕面市立止々呂美小学校':
            add('箕面市立とどろみの森学園', geom, city, '箕面市森町中1-23-14',
                point=[135.461081, 34.886218])
        else:
            add(name, geom, city, addr)

    # A27に校区が無い市区（大阪市東淀川区）: P29の学校位置のみで登録
    for f in p29['features']:
        p = f['properties']
        if p['P29_001'] in POINT_ONLY and p['P29_003'] in ('16001', '16014') \
                and p['P29_004'].startswith('大阪市立'):
            name = p['P29_004']
            schools[name] = {
                'name': name, 'short': name.replace('大阪市立', ''),
                'city': CITIES[p['P29_001']],
                'address': (p['P29_005'] or '').replace('大阪府', ''),
                'point': f['geometry']['coordinates'],
                'polygon': None,
            }

    # A27に校区ポリゴンが無い学校（ピンのみ登録）
    schools['枚方市立禁野小学校'] = {
        'name': '枚方市立禁野小学校', 'short': '禁野小学校', 'city': '枚方市',
        'address': '枚方市中宮北町4-1', 'point': [135.660411, 34.822723],
        'polygon': None,
    }

    st_all = {}
    student_cities = []
    for city, key in CITY_KEYS.items():
        if key in students:
            st_all.update(students[key]['schools'])
            student_cities.append(city)

    out = []
    for e in schools.values():
        assert e['point'], '位置不明: ' + e['name']
        if e['city'] in student_cities:
            assert e['name'] in st_all, '児童数不明: ' + e['name']
        base = e['short'].replace('小学校', '')
        e['yomi'] = yomi.get(base, '')
        e['students'] = st_all.get(e['name'])
        e['point'] = [round(e['point'][0], 6), round(e['point'][1], 6)]
        if e['polygon'] is not None:
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
            'students': {city: {k: students[key][k] for k in ('source', 'sourceUrl', 'asOf')}
                         for city, key in CITY_KEYS.items() if key in students},
        },
        'schools': out,
    }
    dst = os.path.join(here, '..', 'data', 'schools.js')
    with open(dst, 'w') as f:
        f.write('window.SCHOOL_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    from collections import Counter
    c = Counter(e['city'] for e in out)
    print('生成完了: %d校 %s %dKB' % (
        len(out), dict(sorted(c.items())), os.path.getsize(dst) // 1024))


if __name__ == '__main__':
    main(*sys.argv[1:])
