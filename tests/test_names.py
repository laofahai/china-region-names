import csv
import tempfile
import unittest
from pathlib import Path
from tools.names import compile_mapping, read_overrides


def row(code, name, parent='', level='county', namespace='test'):
    return {'id':f'{namespace}:{code}','code':code,'code_system':namespace,'name':name,'parent_id':parent,'level':level,'source_id':'fixture'}


class NamingTests(unittest.TestCase):
    def test_manual_display_collision_preserves_every_full_name(self):
        rows=[row('1','甲县'),row('2','乙县')]
        result,report=compile_mapping(rows,{'test:1':{'name':'甲县','short_name':'甲地','display_name':'乙县','reason':'测试显示冲突'}})
        self.assertEqual([(r['short_name'],r['display_name']) for r in result],[('甲县','甲县'),('乙县','乙县')])
        self.assertIn('乙县',report['short_conflicts'])

    def test_original_same_name_cannot_be_reabbreviated_by_overrides(self):
        rows=[row('1','朝阳区'),row('2','朝阳区')]
        result,_=compile_mapping(rows,{'test:1':{'name':'朝阳区','short_name':'甲地','reason':'测试'},'test:2':{'name':'朝阳区','short_name':'乙地','reason':'测试'}})
        self.assertTrue(all(r['short_name']==r['display_name']==r['name'] for r in result))

    def test_country_is_china_for_every_record(self):
        result,_=compile_mapping([row('71','台湾省',level='province'),row('81','香港特别行政区',level='province'),row('82','澳门特别行政区',level='province')],{})
        self.assertTrue(all(r.get('country_code')=='CN' for r in result))

    def test_non_china_country_assignment_rejected(self):
        r=row('71','台湾省',level='province');r['country_code']='TW'
        with self.assertRaisesRegex(ValueError,'国别'):compile_mapping([r],{})

    def test_cross_province_collision_preserves_both_full_names(self):
        rows=[row('1','甘肃省',level='province'),row('2','黑龙江省',level='province'),row('11','甘南藏族自治州','test:1','prefecture'),row('21','甘南县','test:2')]
        result,_=compile_mapping(rows,{'test:11':{'name':'甘南藏族自治州','short_name':'甘南','reason':'显式简称'}})
        by={r['id']:r for r in result}
        self.assertEqual(by['test:11']['short_name'],'甘南藏族自治州')
        self.assertEqual(by['test:21']['short_name'],'甘南县')

    def test_parent_child_and_sibling_collisions_preserve_every_participant(self):
        rows=[row('1','临夏回族自治州',level='prefecture'),row('11','临夏市','test:1'),row('12','临夏县','test:1')]
        result,report=compile_mapping(rows,{'test:1':{'name':'临夏回族自治州','short_name':'临夏','reason':'审核候选'}})
        self.assertEqual([r['short_name'] for r in result],[r['name'] for r in result])
        self.assertTrue(report['short_conflicts'])

    def test_alias_equal_to_other_full_name_also_conflicts(self):
        result,_=compile_mapping([row('1','东区街道'),row('2','东区')],{})
        self.assertEqual(result[0]['short_name'],'东区街道')
        self.assertEqual(result[1]['short_name'],'东区')

    def test_province_city_conflict_does_not_leave_province_abbreviated(self):
        result,_=compile_mapping([row('1','吉林省',level='province'),row('2','吉林市',level='prefecture')],{})
        self.assertEqual([(r['short_name'],r['display_name']) for r in result],[('吉林省','吉林省'),('吉林市','吉林市')])

    def test_original_same_name_requires_parent_context(self):
        result,report=compile_mapping([row('1','北京市',level='province'),row('2','吉林省',level='province'),row('11','朝阳区','test:1'),row('21','朝阳区','test:2')],{})
        by={r['id']:r for r in result}
        self.assertNotEqual(by['test:11']['qualified_name'],by['test:21']['qualified_name'])
        self.assertTrue(by['test:11']['needs_parent_context'])
        self.assertIn('朝阳区',report['full_name_duplicates'])

    def test_autonomous_names_are_not_guessed_without_csv(self):
        result,_=compile_mapping([row('1','海西蒙古族藏族自治州',level='prefecture'),row('2','鄂温克族自治旗'),row('3','东乡族自治县')],{})
        self.assertEqual([r['short_name'] for r in result],[r['name'] for r in result])

    def test_reviewed_autonomous_override_and_normal_names(self):
        result,_=compile_mapping([row('1','海西蒙古族藏族自治州',level='prefecture'),row('2','温州市',level='prefecture'),row('3','忠县'),row('4','山东省',level='province'),row('5','南江县'),row('6','历下区')],{'test:1':{'name':'海西蒙古族藏族自治州','short_name':'海西','reason':'审核通过'}})
        self.assertEqual([r['short_name'] for r in result],['海西','温州','忠县','山东','南江','历下区'])
        self.assertEqual(result[1]['display_name'],'温州')
        self.assertTrue(all(r['display_name']==r['short_name'] for r in result))

    def test_manual_display_cannot_override_ambiguity(self):
        result,_=compile_mapping([row('1','阿克苏地区',level='prefecture'),row('2','阿克苏市')],{'test:1':{'name':'阿克苏地区','short_name':'阿克苏','display_name':'阿克苏','reason':'测试强制覆盖'}})
        self.assertEqual(result[0]['display_name'],'阿克苏地区')

    def test_unknown_parent_rejected(self):
        with self.assertRaisesRegex(ValueError,'上级'):compile_mapping([row('1','测试县','missing')],{})

    def test_parent_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError,'循环'):compile_mapping([row('1','甲县','test:2'),row('2','乙县','test:1')],{})

    def test_duplicate_record_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'重复'):compile_mapping([row('1','甲县'),row('1','乙县')],{})

    def test_stale_override_rejected_instead_of_silently_reused(self):
        with self.assertRaisesRegex(ValueError,'名称'):compile_mapping([row('1','新名称县')],{'test:1':{'name':'旧名称县','short_name':'旧名称','reason':'过期映射'}})

    def test_missing_override_target_rejected(self):
        with self.assertRaisesRegex(ValueError,'不存在'):compile_mapping([],{'test:missing':{'name':'不存在县','short_name':'不存在','reason':'过期'}})

    def test_empty_name_rejected(self):
        with self.assertRaisesRegex(ValueError,'名称'):compile_mapping([row('1','')],{})

    def test_override_csv_does_not_overwrite_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'overrides.csv'
            p.write_text('id,name,short_name,display_name,reason\ntest:1,甲县,甲,,说明\ntest:1,甲县,乙,,说明\n')
            with self.assertRaisesRegex(ValueError,'重复'):read_overrides(p)

    def test_output_is_deterministic_for_same_input(self):
        rows=[row('1','山东省',level='province'),row('2','济南市','test:1','prefecture')]
        self.assertEqual(compile_mapping(rows,{}),compile_mapping(rows,{}))


if __name__=='__main__':unittest.main()
