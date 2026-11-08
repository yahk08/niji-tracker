"""CSVからライバー名簿JSONを作成。channel_id は実在する UC... ID を指定。"""
import csv,json,re,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/members.csv'
with source.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
items=[];seen=set();errors=[]
for line,r in enumerate(rows,2):
    name=(r.get('name') or '').strip(); group=(r.get('group') or 'JP').strip().upper(); channel=(r.get('channel_id') or '').strip(); alias=(r.get('alias') or '').strip()
    if not name:continue
    if group not in ('JP','EN','KR','ID','OTHER'): errors.append(f'{line}行: groupはJP/EN/KR/ID/OTHER');continue
    if not re.fullmatch(r'UC[\w-]{22}',channel):errors.append(f'{line}行: {name} のchannel_idが不正（UCから始まる24文字）');continue
    if channel in seen:errors.append(f'{line}行: {name} のchannel_id重複');continue
    seen.add(channel);items.append({'id':channel,'name':name,'group':'other' if group=='OTHER' else group,'channel_id':channel,'alias':alias})
if errors:raise SystemExit('\n'.join(errors))
(ROOT/'data/members.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(items)}名を登録しました。現役全員かどうかは別途確認してください。')
