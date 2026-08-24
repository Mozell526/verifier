import json
import pandas as pd

p = '/Users/xiaozijian/Downloads/verifier-client_search-cases-port8024-20260812-080210.xlsx'
df = pd.read_excel(p, sheet_name='用例池候选区').fillna('')

def parse(v):
    if isinstance(v, dict): return v
    try: return json.loads(v)
    except: return {}

want = ['I031','I033','I046','I060','I088','I090','I092','I093','I114','I127','I149','I161','I318','I377','I419','I463','I481','I495','I525','I554','I626','I633','I643']
for _, r in df.iterrows():
    i = str(r['ID'])
    if i not in want: continue
    o = parse(r['Output / 被评估输出']); rr = parse(r['Reference'])
    print(json.dumps({'id': i, 'status': str(r['状态']), 'query': parse(r['Input / Live Request']).get('user_text',''),
                      'live_conds': [(c.get('field'), c.get('operator'), c.get('value')) for c in (o.get('conditions') or [])],
                      'ref_conds': [(c.get('field'), c.get('operator'), c.get('value')) for c in (rr.get('conditions') or [])],
                      'robot_text': str(o.get('robot_text') or '')[:160]}, ensure_ascii=False))
