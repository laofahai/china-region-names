"""离线生成名称表；只读人工CSV，不联网、不改写输入。"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from tools.names import compile_mapping, read_overrides


def load_sources(root):
    manifest=json.loads((root/'sources/manifest.json').read_text())
    for item in manifest['files']:
        actual=hashlib.sha256((root/item['path']).read_bytes()).hexdigest()
        if actual!=item['sha256']:raise ValueError('来源校验失败：'+item['path'])
    pairs=[line.split(maxsplit=1) for line in (root/'sources/areacodes-2025.txt').read_text().splitlines() if line.strip()]
    codes={code for code,name in pairs}
    records=[]
    for code,name in pairs:
        level='province' if code.endswith('0000') else 'prefecture' if code.endswith('00') else 'county'
        parent='' if level=='province' else code[:2]+'0000'
        if level=='county' and code[:4]+'00' in codes:parent=code[:4]+'00'
        records.append({'id':'mca:'+code,'code':code,'code_system':'mca','name':name,'level':level,'parent_id':'mca:'+parent if parent else '', 'source_id':'areacodes-2025','kind':'administrative','code_status':'source_published'})
    supplement=json.loads((root/'sources/supplement-2026-11-13.json').read_text())
    records+=supplement['records']
    return records,manifest


SELECTOR_GROUPS={
    '1101':('110000','市辖区'), '1201':('120000','市辖区'), '3101':('310000','市辖区'),
    '5001':('500000','市辖区'), '5002':('500000','县'),
    '4190':('410000','省直辖县级行政区划'), '4290':('420000','省直辖县级行政区划'),
    '4690':('460000','省直辖县级行政区划'), '6590':('650000','自治区直辖县级行政区划'),
}


def build(root):
    records,manifest=load_sources(root)
    overrides=read_overrides(root/'data/overrides.csv')
    normal={k:v for k,v in overrides.items() if not k.startswith('selector:')}
    compiled,report=compile_mapping(records,normal)
    groups=[]
    for code,(parent,name) in SELECTOR_GROUPS.items():
        key='selector:'+code;override=overrides.get(key)
        if not override or override['name']!=name or not override['short_name'] or not override['display_name']:raise ValueError('选择器分组缺少有效映射：'+key)
        groups.append({'id':key,'code':code,'code_system':'selector_group','parent_id':'mca:'+parent,'name':name,'short_name':override['short_name'],'display_name':override['display_name'],'kind':'selector_group','reason':override['reason']})
    unknown_groups={k for k in overrides if k.startswith('selector:')}-{g['id'] for g in groups}
    if unknown_groups:raise ValueError('未知选择器分组映射：'+','.join(sorted(unknown_groups)))
    compiled.sort(key=lambda r:(r['code_system'],r['code'],r['id']))
    report['by_level']=dict(sorted(Counter(r['level'] for r in compiled).items()))
    report['by_source']=dict(sorted(Counter(r['source_id'] for r in compiled).items()))
    report['needs_parent_context']=sum(r['needs_parent_context'] for r in compiled)
    report['selector_groups']=len(groups)
    out=root/'dist';out.mkdir(exist_ok=True)
    def dump(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    dump('mapping.json',{'schema_version':1,'base_as_of':'2025-12-31','supplement_checked_on':'2026-11-13','records':compiled})
    dump('ambiguities.json',report)
    dump('selector-groups.json',groups)
    fields=['id','country_code','code_system','code','level','kind','parent_id','name','candidate_name','short_name','display_name','qualified_name','needs_parent_context','code_status','source_id','reason']
    with (out/'mapping.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(compiled)
    return compiled,report


def main():
    parser=argparse.ArgumentParser(description='离线生成简体行政区划名称映射')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    _,report=build(args.root)
    print(json.dumps({k:v for k,v in report.items() if k not in ('short_conflicts','full_name_duplicates')},ensure_ascii=False))
    print('简称冲突组：',len(report['short_conflicts']),'正式全名同名组：',len(report['full_name_duplicates']))


if __name__=='__main__':main()
