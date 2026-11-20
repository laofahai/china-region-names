import hashlib
import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from shutil import copytree
from tools.build import build, load_sources

ROOT=Path(__file__).resolve().parents[1]


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records,cls.report=build(ROOT)
        cls.by_id={r['id']:r for r in cls.records}

    def test_all_34_province_units_including_taiwan_hongkong_macau(self):
        provinces=[r for r in self.records if r['level']=='province']
        self.assertEqual(len(provinces),34)
        self.assertEqual({self.by_id[k]['name'] for k in ['mca:710000','mca:810000','mca:820000']},{'台湾省','香港特别行政区','澳门特别行政区'})

    def test_taiwan_household_counties_and_towns_are_complete(self):
        rows=[r for r in self.records if r['source_id']=='nlsc-household-20261113']
        self.assertEqual(sum(r['level']=='local_county_city' for r in rows),22)
        self.assertEqual(sum(r['level']=='township' for r in rows),368)
        keys=[(r['parent_id'],r['name']) for r in rows]
        self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(self.by_id['tw-local:10020']['name'],'嘉义市')

    def test_hongkong_and_macau_levels_not_falsely_labeled_county(self):
        hk=[r for r in self.records if r['code_system']=='community_hk-district']
        mo=[r for r in self.records if r['code_system']=='community_mo-area']
        self.assertEqual(len(hk),18)
        self.assertTrue(all(r['name'].endswith('区') for r in hk))
        self.assertEqual(sum(r['kind']=='parish' for r in mo),7)
        self.assertEqual(sum(r['kind']=='geographic_area' for r in mo),1)
        self.assertIn('花地玛堂区',{r['name'] for r in mo})
        self.assertNotIn('花马地堂区',{r['name'] for r in mo})

    def test_kinmen_and_lienchiang_not_reparented_to_taiwan(self):
        rows=[r for r in self.records if r['level']=='local_county_city' and r['name'] in ('金门县','连江县')]
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['parent_id']=='mca:350000' for r in rows))

    def test_short_name_collisions_only_remain_for_identical_full_names(self):
        groups=defaultdict(list)
        for r in self.records:groups[r['short_name']].append(r)
        for label,rows in groups.items():
            self.assertEqual(len({r['name'] for r in rows}),1,(label,[r['name'] for r in rows]))
            if len(rows)>1:self.assertTrue(all(r['short_name']==r['name'] and r['needs_parent_context'] for r in rows))

    def test_every_conflict_participant_has_both_full_fields(self):
        keys={k for ids in self.report['short_conflicts'].values() for k in ids}
        for key in keys:
            r=self.by_id[key]
            self.assertEqual(r['short_name'],r['name'])
            self.assertEqual(r['display_name'],r['name'])

    def test_four_city_no_county_shape_does_not_invent_children(self):
        for code in ['441900','442000','460400','620200']:
            r=self.by_id['mca:'+code]
            self.assertEqual(r['level'],'prefecture')
            self.assertFalse(any(x['parent_id']==r['id'] and x['level']=='county' for x in self.records))

    def test_selector_groups_are_separate_ui_records(self):
        groups=json.loads((ROOT/'dist/selector-groups.json').read_text())
        self.assertEqual(len(groups),9)
        self.assertEqual(next(g['display_name'] for g in groups if g['id']=='selector:5002'),'重庆市辖县')
        self.assertFalse(set(g['id'] for g in groups)&set(self.by_id))

    def test_notice_name_does_not_invent_official_code(self):
        r=self.by_id['notice:cenling-20260326']
        self.assertEqual(r['name'],'岑岭县')
        self.assertEqual(r['code'],'')
        self.assertEqual(r['code_status'],'name_verified_code_unverified')

    def test_no_empty_names_and_known_traditional_forms(self):
        forbidden=set('臺灣縣鄉鎮區東蓮義島門廣雲慶漢蘇龍')
        for r in self.records:
            for f in ('name','short_name','display_name'):
                self.assertTrue(r[f])
                self.assertFalse(set(r[f])&forbidden,(r['id'],f,r[f]))

    def test_shortened_autonomous_names_do_not_leave_partial_ethnic_suffixes(self):
        for r in self.records:
            if '自治' in r['name'] and r['short_name']!=r['name']:
                self.assertNotIn('族',r['short_name'],r['id'])
        self.assertEqual(self.by_id['mca:530925']['short_name'],'双江')

    def test_build_reproducible_and_does_not_rewrite_manual_csv(self):
        names=['mapping.json','mapping.csv','ambiguities.json','selector-groups.json']
        before={n:hashlib.sha256((ROOT/'dist'/n).read_bytes()).hexdigest() for n in names}
        manual=(ROOT/'data/overrides.csv').read_bytes()
        build(ROOT)
        self.assertEqual(before,{n:hashlib.sha256((ROOT/'dist'/n).read_bytes()).hexdigest() for n in names})
        self.assertEqual(manual,(ROOT/'data/overrides.csv').read_bytes())

    def test_changed_source_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            copytree(ROOT/'sources',target/'sources')
            with (target/'sources/areacodes-2025.txt').open('a') as stream:stream.write('\n')
            with self.assertRaisesRegex(ValueError,'校验'):load_sources(target)
