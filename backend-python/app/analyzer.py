"""
招标文件分析器 - 实现用户提供的语义分析和模式识别逻辑
"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DisqualificationItem:
    """废标项"""
    category: str  # 资格性审查/符合性审查/实质性技术条款/法律禁止行为
    content: str
    source: str
    risk_level: str  # 高/中/低
    keywords: List[str] = field(default_factory=list)


@dataclass
class ScoringItem:
    """评分项"""
    category: str  # 价格分/技术分/商务分/服务分
    factor: str
    score: str
    criteria: str
    proof_required: str
    notes: str = ""


@dataclass
class BusinessTerm:
    """商务条款"""
    term_type: str  # 时间/金额/地点/人员/其他
    content: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TechnicalRequirement:
    """技术需求"""
    param_id: str
    param_name: str
    requirement: str
    is_essential: bool  # ★ 实质性
    is_demo: bool  # # 演示项
    is_important: bool  # ▲ 重要
    proof_required: str = ""


@dataclass
class TenderAnalysis:
    """招标分析结果"""
    project_info: Dict[str, str] = field(default_factory=dict)
    disqualification_items: List[DisqualificationItem] = field(default_factory=list)
    scoring_criteria: List[ScoringItem] = field(default_factory=list)
    business_terms: List[BusinessTerm] = field(default_factory=list)
    technical_requirements: List[TechnicalRequirement] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    checklists: List[str] = field(default_factory=list)


class TenderDocumentAnalyzer:
    """
    招标文件分析器
    基于语义分析和模式识别，从不规则的招标文件文本中提取标准化信息
    """
    
    # 废标项识别模式
    DISQUALIFICATION_PATTERNS = [
        r"(废标|否决投标|无效投标|投标无效|资格审查不合格|符合性审查不合格).{0,30}(条件|情形|规定|条款)",
        r"★.{0,100}(必须|须|应).{0,50}(满足|提供|响应)",
        r"(资格性审查|符合性审查).{0,50}(内容|包括|要求|标准)",
        r"不满足.{0,20}(任一|任何|以下).{0,20}(条件|要求).{0,20}废标",
        r"有一项.{0,10}不符合.{0,20}废标",
        r"《政府采购法》.{0,10}第.{0,5}条",
        r"(重大违法记录|串通投标|弄虚作假|行贿).{0,30}(拒绝|否决|无效)",
    ]
    
    # 评分标准识别模式
    SCORING_PATTERNS = [
        r"(评分标准|评审因素|评分办法|评标办法|评审细则).{0,50}(\d+\s*分)",
        r"(价格分|技术分|商务分|服务分).{0,30}(\d+\s*分?)",
        r"(演示|答辩|述标).{0,20}(分钟|时长|时间)",
        r"不接受\s*PPT",
        r"(现场演示|视频演示|远程演示)",
    ]
    
    # 商务条款识别模式
    BUSINESS_PATTERNS = {
        "时间": [
            r"(合同签订后|交货期|工期|实施周期|交付期).{0,20}(\d+\s*(天|日|工作日|日历日))",
            r"(质保期|维护期|保修期).{0,20}(\d+\s*(年|月|天))",
            r"投标有效期.{0,20}(\d+\s*(天|日|日历日))",
        ],
        "金额": [
            r"(预算金额|最高限价|控制价).{0,10}[¥￥]?\s*(\d+[\.,]?\d*\s*[万亿]?元?)",
            r"(投标保证金|履约保证金).{0,20}(\d+[\.,]?\d*\s*%?\s*元?)",
            r"(预付款|验收款|质保金).{0,10}(\d+\s*%)",
        ],
        "地点": [
            r"(交货地点|实施地点|服务地点|项目地点).{0,30}([\u4e00-\u9fa5]{2,20})",
        ],
        "人员": [
            r"(驻场人员|项目经理|技术人员).{0,20}(\d+\s*人)",
            r"(项目经理|技术负责人).{0,20}(具备|持有|有).{0,20}(证书|资质|PMP)",
        ],
    }
    
    # 技术参数标记
    TECH_MARKERS = {
        "essential": "★",      # 实质性条款
        "important": "▲",      # 重要参数
        "demo": "#",           # 演示项
        "key": "*",            # 关键参数
    }
    
    def __init__(self):
        self.raw_text = ""
        self.analysis = TenderAnalysis()
    
    def analyze(self, raw_text: str) -> TenderAnalysis:
        """
        主分析入口
        1. 全文检索关键语义模式
        2. 识别招标类型
        3. 动态组装分析结果
        """
        self.raw_text = raw_text
        
        # 1. 提取废标项
        self._extract_disqualification_items()
        
        # 2. 提取评分标准
        self._extract_scoring_criteria()
        
        # 3. 提取商务条款
        self._extract_business_terms()
        
        # 4. 提取技术需求
        self._extract_technical_requirements()
        
        # 5. 提取项目基本信息
        self._extract_project_info()
        
        # 6. 生成注意事项和检查清单
        self._generate_notes_and_checklists()
        
        return self.analysis
    
    def _extract_by_patterns(self, text: str, patterns: List[str]) -> List[Dict]:
        """基于模式提取内容"""
        results = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # 提取匹配位置前后文
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                
                results.append({
                    "match": match.group(),
                    "context": context,
                    "position": match.start()
                })
        return results
    
    def _extract_disqualification_items(self):
        """提取废标项"""
        matches = self._extract_by_patterns(self.raw_text, self.DISQUALIFICATION_PATTERNS)
        
        for match in matches:
            content = match["context"]
            
            # 分类判断
            category = self._classify_disqualification(content)
            risk_level = self._assess_risk_level(content)
            
            item = DisqualificationItem(
                category=category,
                content=content[:300],  # 限制长度
                source=f"位置: {match['position']}",
                risk_level=risk_level,
                keywords=self._extract_keywords(content)
            )
            self.analysis.disqualification_items.append(item)
        
        # 去重
        seen = set()
        unique_items = []
        for item in self.analysis.disqualification_items:
            key = item.content[:100]
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        self.analysis.disqualification_items = unique_items
    
    def _classify_disqualification(self, content: str) -> str:
        """分类废标项类型"""
        content_lower = content.lower()
        
        if any(kw in content_lower for kw in ["资格", "营业执照", "资质证书", "财务审计", "纳税", "社保"]):
            return "资格性审查"
        elif any(kw in content_lower for kw in ["签字", "盖章", "密封", "份数", "保证金", "有效期"]):
            return "符合性审查"
        elif "★" in content or "实质性" in content_lower:
            return "实质性技术条款"
        elif any(kw in content_lower for kw in ["违法", "串通", "作假", "行贿"]):
            return "法律禁止行为"
        return "其他"
    
    def _assess_risk_level(self, content: str) -> str:
        """评估风险等级"""
        high_risk_keywords = ["★", "必须", "须", "应当", "否决", "拒绝"]
        if any(kw in content for kw in high_risk_keywords):
            return "高"
        elif any(kw in content for kw in ["应", "提供", "具备"]):
            return "中"
        return "低"
    
    def _extract_scoring_criteria(self):
        """提取评分标准"""
        matches = self._extract_by_patterns(self.raw_text, self.SCORING_PATTERNS)
        
        # 尝试找到评分表格区域
        scoring_sections = self._find_scoring_sections()
        
        for section in scoring_sections:
            item = ScoringItem(
                category=section.get("category", "其他"),
                factor=section.get("factor", ""),
                score=section.get("score", ""),
                criteria=section.get("criteria", ""),
                proof_required=section.get("proof", ""),
                notes=section.get("notes", "")
            )
            self.analysis.scoring_criteria.append(item)
    
    def _find_scoring_sections(self) -> List[Dict]:
        """查找评分标准区域"""
        sections = []
        
        # 查找评分相关段落
        scoring_keywords = ["评分标准", "评审因素", "评标办法", "评分细则"]
        for keyword in scoring_keywords:
            pattern = rf"{keyword}.{{0,500}}"
            matches = re.finditer(pattern, self.raw_text, re.DOTALL)
            for match in matches:
                text = match.group()
                # 解析评分项
                lines = text.split('\n')
                for line in lines:
                    if any(c.isdigit() for c in line) and '分' in line:
                        sections.append({
                            "category": self._detect_scoring_category(line),
                            "factor": line[:50],
                            "score": self._extract_score(line),
                            "criteria": line,
                            "proof": "",
                            "notes": ""
                        })
        
        return sections
    
    def _detect_scoring_category(self, text: str) -> str:
        """检测评分类别"""
        text_lower = text.lower()
        if "价格" in text_lower or "报价" in text_lower:
            return "价格分"
        elif "技术" in text_lower or "参数" in text_lower:
            return "技术分"
        elif "商务" in text_lower or "业绩" in text_lower or "证书" in text_lower:
            return "商务分"
        elif "服务" in text_lower or "售后" in text_lower or "实施" in text_lower:
            return "服务分"
        return "其他"
    
    def _extract_score(self, text: str) -> str:
        """提取分值"""
        match = re.search(r'(\d+)\s*分', text)
        return match.group(1) + "分" if match else ""
    
    def _extract_business_terms(self):
        """提取商务条款"""
        for term_type, patterns in self.BUSINESS_PATTERNS.items():
            matches = self._extract_by_patterns(self.raw_text, patterns)
            for match in matches:
                term = BusinessTerm(
                    term_type=term_type,
                    content=match["context"][:200],
                    details={"source": match["match"]}
                )
                self.analysis.business_terms.append(term)
    
    def _extract_technical_requirements(self):
        """提取技术需求"""
        # 查找技术参数表
        tech_sections = self._find_technical_sections()
        
        for section in tech_sections:
            req = TechnicalRequirement(
                param_id=section.get("id", ""),
                param_name=section.get("name", ""),
                requirement=section.get("requirement", ""),
                is_essential="★" in section.get("markers", ""),
                is_demo="#" in section.get("markers", ""),
                is_important="▲" in section.get("markers", ""),
                proof_required=section.get("proof", "")
            )
            self.analysis.technical_requirements.append(req)
    
    def _find_technical_sections(self) -> List[Dict]:
        """查找技术参数区域"""
        sections = []
        
        # 查找技术规格相关段落
        tech_keywords = ["技术参数", "技术规格", "采购需求", "功能需求", "技术要求"]
        for keyword in tech_keywords:
            # 查找关键词后的表格或列表内容
            pattern = rf"{keyword}.{{0,2000}}"
            matches = re.finditer(pattern, self.raw_text, re.DOTALL)
            for match in matches:
                text = match.group()
                lines = text.split('\n')
                for line in lines:
                    # 检测标记符号
                    markers = ""
                    if "★" in line:
                        markers += "★"
                    if "▲" in line:
                        markers += "▲"
                    if "#" in line:
                        markers += "#"
                    
                    if markers or any(kw in line for kw in ["参数", "指标", "要求"]):
                        sections.append({
                            "id": "",
                            "name": line[:100],
                            "requirement": line,
                            "markers": markers,
                            "proof": ""
                        })
        
        return sections
    
    def _extract_project_info(self):
        """提取项目基本信息"""
        # 项目名称
        name_match = re.search(r'项目名称[：:]\s*([^\n]+)', self.raw_text)
        if name_match:
            self.analysis.project_info["项目名称"] = name_match.group(1).strip()
        
        # 项目编号
        code_match = re.search(r'项目编号[：:]\s*([^\n]+)', self.raw_text)
        if code_match:
            self.analysis.project_info["项目编号"] = code_match.group(1).strip()
        
        # 预算金额
        budget_match = re.search(r'(预算金额|最高限价)[：:]\s*([^\n]+)', self.raw_text)
        if budget_match:
            self.analysis.project_info["预算金额"] = budget_match.group(2).strip()
        
        # 采购人
        buyer_match = re.search(r'(采购人|招标人)[：:]\s*([^\n]+)', self.raw_text)
        if buyer_match:
            self.analysis.project_info["采购人"] = buyer_match.group(2).strip()
    
    def _generate_notes_and_checklists(self):
        """生成注意事项和检查清单"""
        # 基于提取的内容生成
        if any(item.is_demo for item in self.analysis.technical_requirements):
            self.analysis.notes.append("⚠️ 本项目要求现场演示，请提前准备演示环境")
        
        if any("PPT" in item.notes for item in self.analysis.scoring_criteria):
            self.analysis.notes.append("📋 注意评分标准中对演示形式的限制")
        
        # 生成检查清单
        self.analysis.checklists = [
            "□ 核对所有★号参数是否完全响应",
            "□ 确认签字盖章位置及要求",
            "□ 检查投标文件份数（正本/副本/电子版）",
            "□ 确认保证金金额及缴纳方式",
            "□ 核对业绩时间范围要求",
        ]
        
        # 根据废标项添加检查项
        for item in self.analysis.disqualification_items:
            if item.risk_level == "高":
                self.analysis.checklists.append(f"□ 【高】{item.content[:30]}...")
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        keywords = []
        keyword_patterns = ["必须", "须", "应", "应当", "提供", "具备", "满足"]
        for kw in keyword_patterns:
            if kw in content:
                keywords.append(kw)
        return keywords
    
    def classify_document_type(self) -> str:
        """识别招标类型（货物/服务/工程）"""
        text_lower = self.raw_text.lower()
        
        if any(kw in text_lower for kw in ["货物", "设备", "产品", "硬件", "软件"]):
            return "货物"
        elif any(kw in text_lower for kw in ["服务", "运维", "维护", "咨询", "设计"]):
            return "服务"
        elif any(kw in text_lower for kw in ["工程", "施工", "建设", "装修"]):
            return "工程"
        return "其他"
