# china-region-names

中国行政区划名称、简称和显示名称映射。名称统一使用简体，覆盖34个省级单元，并补充台湾地区本地户政、香港18区及澳门堂区等名称。

按中国行政区划口径，所有记录国别统一为中国（`country_code=CN`）。台湾为台湾省，香港、澳门为特别行政区，均纳入中国34个省级单元。不同来源的编码体系仅作技术区分，不代表不同国家。

**人工只维护 [`data/overrides.csv`](data/overrides.csv) 一份映射。完整 JSON、CSV 和歧义报告由公开底表与映射生成。**

## 使用数据

| 文件 | 用途 |
|---|---|
| [`dist/mapping.json`](dist/mapping.json) | 完整逐条映射及版本信息 |
| [`dist/mapping.csv`](dist/mapping.csv) | 与JSON同口径的扁平表，适合Excel和批量导入 |
| [`dist/ambiguities.json`](dist/ambiguities.json) | 跨省、跨城市、跨层级的简称冲突与正式同名清单 |
| [`dist/selector-groups.json`](dist/selector-groups.json) | 9条常见三级选择器中间分组标签，与真实区划分开 |
| [`sources/manifest.json`](sources/manifest.json) | 来源、版本、编码体系、校验值及覆盖边界 |

```python
import json
from pathlib import Path

records = json.loads(Path("dist/mapping.json").read_text())["records"]
by_id = {row["id"]: row for row in records}
print(by_id["mca:370000"]["short_name"])  # 山东
print(by_id["mca:653200"]["short_name"])  # 和田地区
```

`id`包含编码体系。不要仅凭一个数字编码跨来源合并记录，也不要用简称作为唯一键。

| 字段 | 含义 |
|---|---|
| `name` | 完整名称，简体 |
| `candidate_name` | 审核冲突前的候选简称，不用于自动关联 |
| `short_name` | 无歧义时可简称；有歧义则保留完整名称 |
| `display_name` | 通用显示名称；普通地级和县级名称保留全称，省份无歧义才简称 |
| `qualified_name` | 包含全部上级的完整路径，供正式同名记录消歧 |
| `needs_parent_context` | 全名仍然重名，展示时需要上级信息 |
| `code_system` / `code_status` | 编码来源及是否已核实；社区标识不冒充官方代码 |
| `source_id` / `reason` | 对应来源和名称处理原因 |

## 简称规则

1. 对完整输入集合检查简称与简称、简称与其他正式名称的冲突，不限于同一个省或父级。
2. 所有冲突参与方的`short_name`、`display_name`都保留正式全称，人工映射也不能绕过此规则。
3. 吉林省/吉林市、海南省/海南藏族自治州、兴安盟/兴安县、阿克苏地区/阿克苏市、临夏市/临夏县等不能只留下一个无层级简称。
4. 朝阳区、鼓楼区等全名本来就同名的记录，仍需要上级路径及稳定ID。保留全称不代表名称天然唯一。
5. 自治州、自治县等复杂名称采用CSV中显式维护的候选，不在生成器中反复猜测、删除民族名称。没有维护的复杂名称保留全称。
6. 新增底表或更名后重新检查全部名称；过期名称映射、重复ID、空名称、断裂上级和循环上级直接报错。

## 数据范围与版本

当前完整名称表 **3629条**，另有9条独立的选择器分组标签。

| 来源 | 范围 | 版本与说明 |
|---|---|---|
| [yescallop/areacodes](https://github.com/yescallop/areacodes) | 34省级、333地级、2845县级 | 固定提交的2025年末公开年表，CC0 |
| [NLSC户政清单](https://data.gov.tw/dataset/102011) | 22个本地市县、368个乡镇市区 | 2026-11-13查询并转简体；本地户政编码单独标识，不冒充民政编码 |
| [chinese_regions](https://github.com/kamaslau/chinese_regions)及政府名称核对 | 香港18区；澳门7堂区及路氹地理区域 | 社区标识保留独立编码体系；订正澳门错名并补全香港区名 |
| [新疆政府设立公告](https://www.xinjiang.gov.cn/xinjiang/tzgg/202603/285e5d25b8ad4eae8df6b0f0efe847f6.shtml) | 岑岭县 | 名称与喀什地区归属已核实，官方编码尚未在本项目核实，因此编码留空、使用公告标识 |

这是**明确版本的公开底表及补充快照**，不宣称实时覆盖全国所有变更。采集日期、公告日期和数据截至日期分别记录。县级主体之外的全国乡镇、街道、村里尚未完整收录；表中没有子节点不代表实际没有下级。

台湾地区补充名称全部为简体，不另存繁体别名。本地户政中的金门县、连江县保留福建上级；同名的民政记录与本地户政口径不按名称自动合并。

香港18区名称已与[香港地政总署](https://www.landsd.gov.hk/tc/resources/mapping-information/hk-geographic-data.html)核对。澳门堂区、路氹地理区域的性质不同，见[澳门地籍资料](https://cadastre.gis.gov.mo/MGSP_Cad/chn/bak/main_20160628.html)和[政府公报](https://bo.dsaj.gov.mo/bo/ii/2024/35/avisosoficiais_cn.asp)；补充标识不是全国统一县级代码。

## 中国区划与地址选择的特殊情况

### 直辖市不一定天然是“省→地级市→县”三层

北京、天津、上海、重庆本身是省级直辖市。许多地址数据会为三级联动增加“市辖区”等中间分组；重庆还常分成“市辖区”和“县”。它们不能凭同一个显示文本合并。

本项目把这类分组放在独立产物中，不混入真实行政区划表：

| 上级 | 分组原名 | 显示标签 |
|---|---|---|
| 北京市 | 市辖区 | 北京市 |
| 天津市 | 市辖区 | 天津市 |
| 上海市 | 市辖区 | 上海市 |
| 重庆市 | 市辖区 | 重庆市 |
| 重庆市 | 县 | 重庆市辖县 |
| 河南省 | 省直辖县级行政区划 | 河南直辖县级 |
| 湖北省 | 省直辖县级行政区划 | 湖北直辖县级 |
| 海南省 | 省直辖县级行政区划 | 海南直辖县级 |
| 新疆维吾尔自治区 | 自治区直辖县级行政区划 | 新疆直辖县级 |

“直辖县级”不是“只有县”：下面可能有济源市、仙桃市、石河子市等县级市，也可能有神农架林区。分组标识不应冒充真实地级行政建制。

### 东莞、中山、儋州、嘉峪关下面可以直接到镇街

这四个地级市在本项目省地县底表中没有县级子节点，地址可能直接写市与镇、街道。不要为了固定三级选择器凭空创建一个区县，也不要把镇街永久当作县级区划。

一些地址解析工具把沙溪镇等放进输出的“区”字段，是接口兼容用法，并不意味着它变成了县级行政区。农场、园区、管理区等名称也不能仅因能被识别，就当作正式行政区。

### 名称里的“市”“州”“区”不能盲删

- 地级市、县级市都含“市”，字数少不代表层级一致。
- 阿克苏地区与阿克苏市、和田地区与和田市/和田县是不同节点。
- “温州”里的“州”是地名的一部分；不能无限删除词尾。
- 海西蒙古族藏族自治州含多个民族名称，单删一个后缀会留下错误简称。
- 鄂温克族自治旗、东乡族自治县不能删成空字符串。

### 历史区划不是一个简单的旧名到新名替换表

更名、撤销、合并、拆分、部分划转含义不同。旧地址、旧名称和旧代码可能仍有用途；一旧多新时不能默认选一个。当前项目维护名称映射，不提供全国历史辖区自动换算。

## 维护方法

只修改`data/overrides.csv`，每条包含：

```csv
id,name,short_name,display_name,reason
mca:513400,凉山彝族自治州,凉山,,自治名称显式简称
```

`display_name`留空时按默认显示策略生成。`name`必须与锁定底表一致，更名后旧映射会报错，避免无声覆盖。生成器自动执行全范围冲突检查；即使CSV填写了简称，发生歧义仍保留全称。

```bash
python3 -m tools.build
python3 -m unittest discover -s tests -v
```

仅需要Python标准库。构建不联网、不回写人工CSV，相同输入产生相同输出。JSON和完整CSV是产物，不直接修改。

底表升级时先准备新版本来源快照、记录来源日期和校验值，再审核新增、撤销、更名及上级变化，检查旧CSV映射，重建并比较完整差异；不要把更新来源文件等同于已核实所有新变更。

## 自动校验与版本发布

GitHub Actions在推送、Pull Request及手动触发时运行测试、离线重建完整产物，并检查提交的产物与人工映射一致。Action固定到具体提交，工作流只有仓库读取权限，不自动抓取或覆盖来源数据。

本仓库提供数据文件，无需部署服务器。当前不自动发布软件包或创建版本；需要固定引用时，可在审核来源与完整差异后创建Git标签及GitHub Release，并注明数据截至日期和覆盖范围。日常维护提交不等于发布一个新数据版本。

## 相近项目

- [Administrative-divisions-of-China-pro](https://github.com/pandelix/Administrative-divisions-of-China-pro)：已有`short_name`及JSON/SQL简化数据，README标注2023年更新；本次未发现其具备本文的全范围歧义保全契约。
- [china-region](https://github.com/shfshanyue/china-region)：区划代码与查询工具。
- [areacodes](https://github.com/yescallop/areacodes)：县级以上历史代码及新旧代码关系，本项目复用其公开年表。
- [province-city-china](https://github.com/uiwjs/province-city-china)：多格式区划数据及港澳补充。

## 相关项目

- [cpca-linch](https://github.com/laofahai/cpca-linch)：Python中文省市区地址解析，支持部分简称、历史名称提示和归属校验。
- [cpca-rs](https://github.com/laofahai/cpca-rs)：Rust中文省市区地址解析，提供候选归属和识别状态。

## 许可

本项目原创脚本及映射采用[MIT许可](LICENSE)。来源数据分别遵循CC0、MIT及政府数据开放授权，详见[第三方说明](THIRD_PARTY_NOTICES.md)与来源清单；不能把整个底表都重新声明为原创MIT数据。
