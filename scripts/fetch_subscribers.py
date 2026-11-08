"""YouTube Data APIから日次記録を取得。失敗日は過去データを壊さない。"""
import datetime,json,os,pathlib,sys,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
key=os.environ.get('YOUTUBE_API_KEY','').strip()
if not key:raise SystemExit('YOUTUBE_API_KEYが設定されていません')
roster=json.loads((ROOT/'data/members.json').read_text(encoding='utf-8'))
ids=list(dict.fromkeys(m['channel_id'] for m in roster if m.get('channel_id')))
if not ids:raise SystemExit('名簿が空です。data/members.csv と import_members.py で登録してください')
result={}
for i in range(0,len(ids),50):
    batch=ids[i:i+50]
    params=urllib.parse.urlencode({'part':'statistics','id':','.join(batch),'key':key,'maxResults':'50'})
    url='https://www.googleapis.com/youtube/v3/channels?'+params
    request=urllib.request.Request(url,headers={'User-Agent':'NijiTracker/1.0'})
    try:
        with urllib.request.urlopen(request,timeout=30) as response: payload=json.load(response)
    except Exception as exc:raise SystemExit(f'API取得に失敗しました: {type(exc).__name__} (鍵や利用上限を確認)') from exc
    for item in payload.get('items',[]):
        stats=item.get('statistics',{})
        if not stats.get('hiddenSubscriberCount') and 'subscriberCount' in stats:
            result[item['id']]=int(stats['subscriberCount'])
missing=set(ids)-set(result)
if missing:print(f'注意: {len(missing)} チャンネルの登録者数を取得できませんでした',file=sys.stderr)
if not result:raise SystemExit('取得値が0件のため保存しません')
history_path=ROOT/'data/history.json'
history=json.loads(history_path.read_text(encoding='utf-8'))
day=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
history[day]={**history.get(day,{}),**result}
history_path.write_text(json.dumps(dict(sorted(history.items())),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print(f'{day}: {len(result)} / {len(ids)} チャンネルを記録しました')
