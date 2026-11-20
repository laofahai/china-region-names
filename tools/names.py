"""把固定底表和人工名称映射编译成保守、可追溯的静态名称表。"""
import csv
from collections import defaultdict


def read_overrides(path):
    result={}
    with open(path,encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        required={'id','name','short_name','display_name','reason'}
        if not required.issubset(reader.fieldnames or []):raise ValueError('映射CSV缺少必要列')
        for row in reader:
            row={k:(v or '').strip() for k,v in row.items()}
            if not any(row.values()):continue
            key=row['id']
            if not key or not row['name'] or not row['reason']:raise ValueError('映射必须有ID、名称和原因')
            if key in result:raise ValueError('映射ID重复：'+key)
            result[key]=row
    return result


def _candidate(record, override):
    if override.get('short_name'):return override['short_name']
    name=record['name']
    # 复杂自治名称只接受人工审核的CSV映射，不猜民族名或从其中截断。
    if '自治' in name:return name
    suffixes=('特别行政区','省','市') if record['level']=='province' else ('地区','街道','市','县','盟','旗','镇','乡')
    for suffix in suffixes:
        if name.endswith(suffix) and len(name)-len(suffix)>=2:return name[:-len(suffix)]
    return name


def compile_mapping(records, overrides):
    by_id={}
    for record in records:
        key=record['id']
        if key in by_id:raise ValueError('区划ID重复：'+key)
        if not record.get('name','').strip():raise ValueError('区划名称不能为空：'+key)
        if record.get('country_code','CN')!='CN':raise ValueError('区划国别必须为中国CN：'+key)
        by_id[key]=dict(record)
        by_id[key]['country_code']='CN'
    for key,override in overrides.items():
        if key not in by_id:raise ValueError('映射目标不存在：'+key)
        if override.get('name')!=by_id[key]['name']:raise ValueError('映射目标名称已变化：'+key)
        if not override.get('reason'):raise ValueError('映射缺少原因：'+key)
    paths={}
    visiting=set()
    def path(key):
        if key in paths:return paths[key]
        if key in visiting:raise ValueError('上级关系形成循环：'+key)
        visiting.add(key)
        record=by_id[key];parent=record.get('parent_id','')
        if parent and parent not in by_id:raise ValueError('上级不存在：'+parent)
        paths[key]=(path(parent)+[record['name']]) if parent else [record['name']]
        visiting.remove(key)
        return paths[key]
    for key in by_id:path(key)
    names=defaultdict(set);candidates=defaultdict(set);displays=defaultdict(set)
    requested_displays={}
    for key,record in by_id.items():
        names[record['name']].add(key)
        candidate=_candidate(record,overrides.get(key,{}))
        if not candidate:raise ValueError('候选简称不能为空：'+key)
        record['candidate_name']=candidate
        candidates[candidate].add(key)
        display=overrides.get(key,{}).get('display_name') or candidate
        requested_displays[key]=display
        if display!=record['name']:displays[display].add(key)
    short_conflicts={}
    # 正式同名不能靠人为编出不同简称绕过全称保全；人工显示值也必须参与消歧。
    blocked={key for keys in names.values() if len(keys)>1 for key in keys}
    for label in candidates.keys()|displays.keys():
        targets=candidates.get(label,set())|displays.get(label,set())|names.get(label,set())
        if len(targets)>1:
            blocked.update(targets)
            if any(by_id[k]['candidate_name']!=by_id[k]['name'] or requested_displays[k]!=by_id[k]['name'] for k in targets):short_conflicts[label]=sorted(targets)
    for record in by_id.values():
        key=record['id'];name=record['name'];override=overrides.get(key,{})
        ambiguous=key in blocked
        record['short_name']=name if ambiguous else record['candidate_name']
        display=override.get('display_name') or record['short_name']
        record['display_name']=name if ambiguous else display
        record['qualified_name']=' > '.join(paths[key])
        record['needs_parent_context']=len(names[name])>1
        record['reason']='简称存在歧义，保留全称' if ambiguous else override.get('reason') or ('保留全称' if name==record['short_name'] else '常规行政后缀简称')
    report={'short_conflicts':dict(sorted(short_conflicts.items())),'full_name_duplicates':{k:sorted(v) for k,v in sorted(names.items()) if len(v)>1},'record_count':len(by_id)}
    return list(by_id.values()),report
