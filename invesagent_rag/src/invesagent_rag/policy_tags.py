from __future__ import annotations


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "制造业升级": ("制造业", "工业", "技改", "技术改造", "转型升级", "先进制造", "产业升级"),
    "科技创新": ("科技", "创新", "研发", "科研", "知识产权", "高新技术", "成果转化"),
    "招商引资": ("招商", "引资", "外资", "项目落地", "签约项目", "产业项目"),
    "财政金融": ("财政", "税收", "融资", "贷款", "担保", "基金", "债券", "上市"),
    "民生保障": ("民生", "就业", "社保", "医保", "教育", "医疗", "住房", "低保"),
    "基础设施": ("基础设施", "交通", "公路", "铁路", "机场", "水利", "园区", "新区"),
    "生态环保": ("生态", "环保", "污染", "节能", "减排", "绿色", "低碳"),
    "农业农村": ("农业", "农村", "农民", "乡村", "粮食", "畜牧", "新农村"),
    "消费服务": ("消费", "商贸", "旅游", "会展", "服务业", "文旅", "物流"),
    "数字经济": ("数字", "信息化", "互联网", "软件", "大数据", "电子商务", "智能"),
}

POLICY_TOOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "财政补贴": ("补贴", "奖补", "扶持资金", "专项资金", "财政支持"),
    "税费减免": ("减税", "免税", "退税", "税费", "减免", "缓缴"),
    "融资支持": ("贷款", "信贷", "融资", "担保", "债券", "上市", "基金"),
    "招商引资": ("招商", "引资", "对接", "签约", "落地"),
    "项目建设": ("项目", "工程", "开工", "投产", "建设", "竣工"),
    "技术改造": ("技改", "技术改造", "设备更新", "改造提升"),
    "人才政策": ("人才", "引才", "培训", "创业平台", "博士后"),
    "园区平台": ("园区", "开发区", "产业基地", "孵化器", "平台"),
}

INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "制造业": ("制造业", "先进制造", "装备制造"),
    "汽车": ("汽车", "新能源汽车", "整车", "零部件"),
    "电子信息": ("电子", "信息产品", "集成电路", "软件", "通信"),
    "新能源": ("新能源", "光伏", "风电", "锂电", "储能"),
    "钢铁": ("钢铁", "钢材", "冶金"),
    "石化化工": ("石化", "化工", "煤化工", "精细化工"),
    "煤炭": ("煤炭", "煤矿", "焦化", "洗煤"),
    "农业": ("农业", "粮食", "畜牧", "农产品"),
    "文旅": ("旅游", "文旅", "文化产业"),
    "房地产": ("房地产", "住房", "棚户区", "保障房"),
    "银行": ("银行", "信贷", "存款", "贷款", "信用卡", "理财"),
    "证券保险": ("证券", "保险", "经纪", "投行", "承保"),
    "医药生物": ("医药", "药品", "医疗器械", "生物制品"),
    "食品饮料": ("食品", "饮料", "白酒", "乳制品"),
    "公用事业": ("电力", "燃气", "水务", "供热"),
}

COMPANY_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "经营情况": ("经营情况", "主营业务", "业务概要", "经营成果", "管理层讨论"),
    "财务表现": ("营业收入", "归属于上市公司股东", "净利润", "毛利率", "资产负债"),
    "风险因素": ("风险因素", "面临的风险", "信用风险", "市场风险", "流动性风险"),
    "公司治理": ("公司治理", "董事会", "监事会", "股东大会", "独立董事"),
    "研发创新": ("研发", "技术创新", "专利", "核心技术", "知识产权"),
    "资本开支": ("资本开支", "在建工程", "固定资产", "重大投资", "募集资金"),
    "分红融资": ("利润分配", "现金股利", "分红", "融资", "债券", "定向增发"),
    "ESG环保": ("社会责任", "ESG", "环境保护", "绿色", "碳排放", "可持续"),
}


def _match_labels(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    labels = []
    for label, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            labels.append(label)
    return labels


def classify_policy_text(text: str) -> dict[str, list[str]]:
    return {
        "content_categories": _match_labels(text, CATEGORY_KEYWORDS),
        "policy_tools": _match_labels(text, POLICY_TOOL_KEYWORDS),
        "mentioned_industries": _match_labels(text, INDUSTRY_KEYWORDS),
    }


def classify_company_report_text(text: str) -> dict[str, list[str]]:
    return {
        "content_categories": _match_labels(text, COMPANY_CATEGORY_KEYWORDS),
        "policy_tools": [],
        "mentioned_industries": _match_labels(text, INDUSTRY_KEYWORDS),
    }


def classify_text(text: str, source_type: str) -> dict[str, list[str]]:
    if source_type == "company_report":
        return classify_company_report_text(text)
    return classify_policy_text(text)
