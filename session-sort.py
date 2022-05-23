import json
import re
session = None

with open('session.session', 'r') as file:
    session = json.loads(file.read())
    # by_url = lambda x : x['url']
    # by_title = lambda x : x['title']
    srtd=sorted(session['tabs'], key=lambda x : (x['url'],x['title']))
    # listurl=list(set([i['url'] for i in srtd]))
    srtd_norep=[]
    for i in srtd:
        srtd_norep.append(i) if ( i not in srtd_norep and i['title'] not in set([i['title'] for i in srtd_norep]) ) else True
    session['tabs'] = srtd_norep

with open('session.session', 'w', encoding='utf8') as file:
    json.dump(session,file, ensure_ascii=False)