"""にじさんじ非公式WikiのYouTubeチャンネル表を取得し、アプリ用members.jsonへ変換。
公式所属情報そのものではないため、生成後の確認が必要です。
"""
import csv
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit('beautifulsoup4 が必要です: py -m pip install beautifulsoup4')

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://wikiwiki.jp/nijisanji/'
SOURCES = {
    'main': BASE + quote('メンバーデータ一覧/YouTubeチャンネル', safe='/'),
    'overseas': BASE + quote('メンバーデータ一覧・海外/YouTubeチャンネル', safe='/'),
}
CID = re.compile(r'(?<![\w-])(UC[\w-]{22})(?![\w-])')

# Wikipedia などと同様、グレーに色付けされている行は卒業・活動終了等
GRAY_HINTS = ('#c2cad2', '#ebebeb', 'rgb(194, 202, 210)', 'rgb(235, 235, 235)')
STOP_WORDS = ('旧チャンネル', 'サブチャンネル', 'サブch', 'チャンネル停止', 'vodチャンネル', 'twitchのvod')

def download(url):
    req = Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; personal-archive/1.0)', 'Accept-Language':'ja-JP,ja;q=0.9'})
    with urlopen(req, timeout=35) as response:
        content = response.read()
        encoding = response.headers.get_content_charset() or 'utf-8'
    return content.decode(encoding, errors='replace')

def rows_from_page(markup):
    soup = BeautifulSoup(markup, 'html.parser')
    for tr in soup.select('tr'):
        cells = tr.find_all(['td','th'], recursive=False)
        if not cells: continue
        first = cells[0]
        found = None
        for a in first.find_all('a', href=True):
            found = CID.search(a['href'])
            if found:
                name = a.get_text(' ', strip=True)
                break
        if not found: continue
        # 卒業済みライバーはWikiでグレー色の背景になっている。
        styles = ' '.join(str(x.get('style','')) for x in [tr,first,*first.find_all(True)]) .lower().replace(' ','')
        cell_classes = ' '.join(' '.join(x.get('class',[])) for x in [tr,first]).lower()
        raw = str(first).lower().replace(' ','')
        grey = any(h.replace(' ','') in styles or h.replace(' ','') in raw for h in GRAY_HINTS) or ('bgcolor' in cell_classes and 'gray' in cell_classes)
        # Wikiの実際の行では一列目背景が gray で判定可能な想定。判定確認用に出力。
        notes = ' '.join(x.get_text(' ',strip=True) for x in cells[1:]).lower()
        yield {'id':found.group(1), 'name':name, 'gray':grey, 'notes':notes}

def normalize_name(name):
    name = html.unescape(name).strip().lstrip('~')
    for suffix in ['〖NIJISANJI EN〗','〖にじさんじ所属〗','〖にじさんじ〗','〖NIJISANJI / にじさんじ〗','〖NIJISANJI・にじさんじ〗']:
        name=name.replace(suffix,'')
    name = re.sub(r'\s+', ' ',name).strip()
    return name

def collect_main(rows):
    collecting=False; group='JP'; result=[]
    first='UCD-miitqNY3nyukJ4Fnf4_A'
    start_id='UCZ5dNZsqBjBzbBl0l_IdmXg'  # Taka Radjiman
    start_kr='UCzMAP-oh5-pC8j6RlCPf26w'  # Wiffy
    start_jp_again='UCUP8TmlO7NNra88AMqGU_vQ' # 小清水透
    for r in rows:
        if r['id']==first: collecting=True
        if not collecting:continue
        # メインページに海外ライバー表が埋め込まれている場合はここで打ち切る
        if r['id'] in ('UCNDVQnBttqVsTZs7zOZHwWA','UC-JSeFfovhNsEhftt1WHMvg'):
            break
        if r['id']==start_id: group='ID'
        if r['id']==start_kr: group='KR'
        if r['id']==start_jp_again: group='JP'
        if r['gray'] or any(s in r['notes'] for s in STOP_WORDS):continue
        result.append({**r,'group':group})
    return result

def collect_en(rows):
    active=False; result=[]
    for r in rows:
        if r['id']=='UCIeSUTOTkF9Hs7q3SGcO-Ow':active=True # Elira
        if not active:continue
        if r['gray'] or any(s in r['notes'] for s in STOP_WORDS):continue
        result.append({**r,'group':'EN'})
    return result

def main():
    pages={}
    for key,url in SOURCES.items():
        print('取得中:',url,flush=True)
        pages[key]=list(rows_from_page(download(url)))
        print('  チャンネルIDを持つ表の行:',len(pages[key]),flush=True)
    records=collect_main(pages['main'])+collect_en(pages['overseas'])
    # 意図しないWiki構造の変更や一覧の読み込み失敗時に、既存データを保護する。
    counts=Counter(r['group'] for r in records)
    print('抽出内訳:',dict(counts),flush=True)
    if not (counts['JP']>=120 and counts['EN']>=20 and counts['ID']>=5 and counts['KR']>=9):
        raise RuntimeError('抽出数が想定と大きく違います。Wikiのページ構造や卒業フィルターを確認してください。既存ファイルは変更していません。')
    seen=set();members=[]
    for r in records:
        if r['id'] in seen:continue
        seen.add(r['id'])
        members.append({'id':r['id'],'name':normalize_name(r['name']), 'group':r['group'], 'channel_id':r['id'], 'alias':''})
    members.sort(key=lambda x:('JP','EN','KR','ID').index(x['group']) if x['group'] in ('JP','EN','KR','ID') else 99)
    dest=ROOT/'data/members.json'
    tmp=dest.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(members,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(dest)
    with (ROOT/'data/members.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['name','group','channel_id','alias']);writer.writeheader()
        for m in members:writer.writerow({k:m.get(k,'') for k in writer.fieldnames})
    print(f'成功: {len(members)} 人を {dest} に保存しました。',flush=True)
    print('注意: データは非公式Wikiを元にしており、最新所属・全件性を個別検証したものではありません。',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('エラー:',exc,file=sys.stderr)
        sys.exit(1)
