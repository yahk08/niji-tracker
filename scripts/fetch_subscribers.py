"""12時間ごとのAPI取得。既存daily historyは維持、時刻別は月単位で保存。"""
import datetime as dt, json, os, pathlib, sys, urllib.parse, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
TZ=dt.timezone(dt.timedelta(hours=9))
def read(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError: return default

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

key=os.environ.get('YOUTUBE_API_KEY','').strip()
if not key: raise SystemExit('YOUTUBE_API_KEY が未設定です')
individual=read(DATA/'members.json',[])
official=read(DATA/'official_channels.json',[])
channels={}
for m in [*individual,*official]:
    cid=m.get('channel_id')
    if cid and cid.startswith('UC'): channels[cid]=m
if not channels: raise SystemExit('対象チャンネルがありません')
ids=list(channels)
values={}; thumbnails={}; titles={}
for start in range(0,len(ids),50):
    batch=ids[start:start+50]
    args=urllib.parse.urlencode({'part':'statistics,snippet','id':','.join(batch),'key':key,'maxResults':'50'})
    try:
        with urllib.request.urlopen(urllib.request.Request('https://www.googleapis.com/youtube/v3/channels?'+args,headers={'User-Agent':'NijiTracker/2.0'}),timeout=35) as resp: payload=json.load(resp)
    except Exception as ex:
        raise SystemExit(f'YouTube API呼び出し失敗: {type(ex).__name__}（保存せず終了）') from ex
    for item in payload.get('items',[]):
        cid=item['id']; stats=item.get('statistics',{}); snippet=item.get('snippet',{})
        if not stats.get('hiddenSubscriberCount') and stats.get('subscriberCount') is not None:
            values[cid]=int(stats['subscriberCount'])
        thumb=snippet.get('thumbnails',{})
        if thumb:
            url=(thumb.get('medium') or thumb.get('default') or {}).get('url','')
            if url.startswith('https://'): thumbnails[cid]=url
        if snippet.get('title'): titles[cid]=snippet['title']
if not values: raise SystemExit('取得件数0。過去のデータは保持します')
now=dt.datetime.now(TZ)
date=now.date().isoformat()
slot_hour=9 if now.hour<15 else 21
slot=f'{date}T{slot_hour:02}:00:00+09:00'
# 既存の日別履歴は同じ日の取得分で上書きし、未取得分は保持
history=read(DATA/'history.json',{})
history[date]={**history.get(date,{}),**values}
write(DATA/'history.json',dict(sorted(history.items())))
# 月ファイルは履歴として永続保存（フロント側は直近30日だけ読む）
monthfile=DATA/'intraday'/f'{date[:7]}.json'
monthly=read(monthfile,{})
monthly[slot]=values
write(monthfile,dict(sorted(monthly.items())))
# 最終取得状況とアイコンURL
missing=sorted(set(ids)-set(values))
latest={'recorded_at':now.isoformat(timespec='seconds'),'slot':slot,'requested':len(ids),'received':len(values),'missing':missing,'thumbnails':thumbnails,'channel_titles':titles}
write(DATA/'latest.json',latest)
print(f'{slot}: {len(values)}/{len(ids)} 件取得、欠測 {len(missing)} 件')
