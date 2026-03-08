"""
AI 服务模块 - 调用 Moonshot API (Kimi K2.5)
"""
import openai
from typing import Dict, Any, Optional
from app.config import get_settings
import json


class AIService:
    """AI 分析服务"""
    
    def __init__(self, api_key: str = None, model_name: str = None, base_url: str = None):
        self.settings = get_settings()
        # 使用传入的配置或默认配置
        from app.main import api_config
        self.api_key = api_key or api_config.get("api_key") or self.settings.MOONSHOT_API_KEY
        self.model_name = model_name or api_config.get("model_name") or self.settings.MODEL_NAME
        self.base_url = base_url or api_config.get("base_url") or self.settings.MODEL_BASE_URL
        
        # 使用 httpx 客户端避免 proxies 参数问题
        import httpx
        http_client = httpx.Client(timeout=120.0)
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client
        )
    
    def analyze_tender_document(self, document_text: str) -> Dict[str, Any]:
        """
        使用 AI 深度分析招标文件
        """
        # 阶段一：结构化提取
        phase1_prompt = self._build_phase1_prompt(document_text)
        phase1_result = self._call_model(phase1_prompt)
        
        # 阶段二：生成模板
        phase2_prompt = self._build_phase2_prompt(phase1_result)
        phase2_result = self._call_model(phase2_prompt)
        
        return {
            "analysis": phase1_result,
            "template_structure": phase2_result
        }
    
    def _call_model(self, prompt: str, temperature: float = 0.3) -> str:
        """调用 AI 模型"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一位专业的招投标分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=8000
            )
            return response.choices[0].message.content
        except Exception as e:
            # 如果主模型调用失败，尝试备用模型
            error_msg = str(e).lower()
            if "not found" in error_msg or "permission denied" in error_msg or "temperature" in error_msg:
                return self._call_fallback_model(prompt, temperature)
            raise e
    
    def _call_fallback_model(self, prompt: str, temperature: float) -> str:
        """备用模型调用"""
        # 根据主模型选择合适的备用模型
        fallback_models = ["moonshot-v1-32k", "moonshot-v1-8k"]
        
        for model in fallback_models:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一位专业的招投标分析专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=8000
                )
                return f"[使用备用模型 {model}]\n" + response.choices[0].message.content
            except Exception:
                continue
        
        raise Exception("所有模型调用失败")
    
    def _build_phase1_prompt(self, document_text: str) -> str:
        """
        构建阶段一 Prompt - 结构化提取
        基于用户提供的 Prompt 设计
        """
        system_role = """你是一位招标文件结构解析专家。你的任务是通过语义分析和模式识别，从不规则的招标文件文本中提取标准化信息，绝对不能假设内容位于特定章节。"""
        
        discovery_strategy = """
## 发现策略

### 1. 废标项识别
**语义特征：**
- 包含"废标"、"否决投标"、"无效投标"、"投标无效"、"资格审查不合格"、"符合性审查不合格"等关键词
- 引用《政府采购法》第二十二条、第十七条等法律条款
- 出现"不满足以下任一条件"、"有一项不符合即作废标处理"等强制性表述
- 包含★号、*号或加粗强调的实质性条款

**内容类型：**
- 资格性要求：营业执照、财务审计报告、纳税社保、信用查询（信用中国/中国政府采购网）、特定行业资质、联合体限制、关联关系限制
- 符合性要求：签字盖章、密封标记、投标文件份数（正本/副本/电子版）、保证金金额及形式、投标有效期、报价不超过预算
- 实质性响应：技术参数★项负偏离、合同条款负偏离、交货期负偏离、质保期负偏离
- 法律禁止：重大违法记录、串通投标、弄虚作假、行贿

**提取规则：** 无论这些内容出现在"投标人须知"、"评标办法"还是"附件"中，必须全部提取

### 2. 评分标准识别
**语义特征：**
- 标题含"评分"、"评标"、"评审标准"、"评分细则"、"评分办法"
- 包含分值分配（如"价格分30分"、"技术分40分"）
- 出现"评审因素"、"评分标准"、"得分"等表格列名

**动态分类：**
- 价格分：是否低价优先、计算公式（基准价/投标价）、小微企业价格扣除（6%-10%）
- 技术分：技术参数响应（注意查找'▲'、'#'、'★'等特殊标记）、技术方案、样品/演示（视频/PPT/现场）
- 商务分：业绩（合同数量、时间范围）、证书（ISO、CMMI、等保）、人员（项目经理证书、团队资质）
- 服务分：实施方案、售后方案、培训方案、应急响应

**关键提取：** 必须精确提取：演示要求（时长、形式限制如"不接受PPT"）、扣分规则（每项扣几分）、证书具体要求（有效期内、社保证明月份）

### 3. 商务条款识别
**语义特征：**
- 时间相关："合同签订后X天/工作日"、"交货期"、"工期"、"实施周期"、"质保期"、"维护期"
- 金额相关："预算金额"、"最高限价"、"付款方式"、"预付款比例"、"验收款"、"质保金"
- 地点相关："交货地点"、"实施地点"、"服务地点"
- 人员相关："驻场服务"、"项目经理"、"技术人员数量"
- 其他："履约保证金"、"保险"、"知识产权归属"、"保密协议"

### 4. 技术需求识别
**语义特征：**
- 功能列表、技术参数表、性能指标、"技术规格"、"采购需求"
- 标记符号：★（实质性）、▲（重要）、#（演示项）、*（关键）
- 参数类型：性能参数（并发数、响应时间、准确率）、功能参数（支持XX功能）、接口参数（API、SDK）、安全参数（等保、密级）

**结构化提取：** 保持原表格结构，提取：参数编号、参数名称、参数要求、是否实质性（★）、是否演示项（#）、证明材料要求

## 自适应规则
- 如果找不到"废标项"章节，查找"投标人须知"中的"无效投标"、"拒绝接收"条款
- 如果找不到"评分标准"，查找"评标办法"、"评审办法"、"评审细则"
- 如果技术参数分散在多章（如"采购需求"、"技术规格书"），全部合并提取
- 如果存在"前附表"、"须知前附表"，优先提取（通常包含关键商务信息摘要）
- 如果招标文件是PDF且结构混乱（如扫描件），基于语义段落重组，不依赖原章节号
"""
        
        output_schema = """
## 输出格式（JSON）

请按以下 JSON 格式输出分析结果：

```json
{
  "project_info": {
    "项目名称": "",
    "项目编号": "",
    "采购人": "",
    "代理机构": "",
    "预算金额": "",
    "招标类型": "货物/服务/工程"
  },
  "disqualification_items": [
    {
      "category": "资格性审查/符合性审查/实质性技术条款/法律禁止行为",
      "content": "废标条款原文",
      "risk_level": "高/中/低"
    }
  ],
  "scoring_criteria": [
    {
      "category": "价格分/技术分/商务分/服务分",
      "factor": "评审因素",
      "score": "分值",
      "criteria": "评分细则",
      "proof_required": "证明材料要求"
    }
  ],
  "business_terms": {
    "delivery_time": "交货期/工期",
    "payment_terms": "付款方式",
    "warranty_period": "质保期",
    "bid_bond": "投标保证金",
    "performance_bond": "履约保证金"
  },
  "technical_requirements": [
    {
      "param_id": "参数编号",
      "param_name": "参数名称",
      "requirement": "参数要求",
      "is_essential": true/false,
      "is_demo": true/false,
      "is_important": true/false,
      "proof_required": "证明材料"
    }
  ],
  "notes": ["注意事项1", "注意事项2"],
  "checklists": ["检查项1", "检查项2"]
}
```
"""
        
        prompt = f"""{system_role}

{discovery_strategy}

{output_schema}

---

**招标文件内容：**

{document_text[:15000]}  # 限制长度避免超出上下文

---

请分析上述招标文件，按输出格式要求返回 JSON 格式的分析结果。确保提取所有废标项、评分标准、商务条款和技术需求。"""
        
        return prompt
    
    def _build_phase2_prompt(self, phase1_result: str) -> str:
        """
        构建阶段二 Prompt - 生成投标文件模板结构
        基于用户提供的 Prompt 设计
        """
        system_role = """你是一位智能投标文件生成器。你接收阶段一提取的结构化数据，根据实际存在的内容动态生成投标文件模板，如果某类内容在招标文件中未要求，则相应章节标记为"[本项目无此要求]"或省略，绝对不要生成固定不变的章节。"""
        
        dynamic_assembly = """
## 动态组装规则

### 1. 封面
始终生成，包含动态提取的项目名称、编号

### 2. 评标索引
**生成条件：** 如果阶段一提取到评分标准
**内容：** 根据实际评分项（可能是价格+技术+商务，也可能是价格+服务+业绩）动态生成表格行，预留页码栏

### 3. 资格证明章节
**动态内容：**
- 如果有"营业执照要求" -> 生成营业执照复印件占位
- 如果有"财务报告要求" -> 生成财务报表/审计报告占位（注意"成立未满X月可不提供"的提示）
- 如果有"纳税社保要求" -> 生成纳税凭据、社保缴纳证明占位
- 如果有"信用查询要求" -> 生成信用中国/政府采购网截图占位
- 如果有"特定资质"（如ISO、等保、CMMI）-> 生成相应证书占位
- 如果有"人员资质要求"（如PMP、高级工程师）-> 生成人员简历+证书+社保占位

**无要求处理：** 如果某项资格在废标项清单中未出现，不生成对应承诺函

### 4. 技术响应章节
**动态表格：**
- 如果发现★号参数 -> 生成"实质性技术条款响应表"（必须完全响应，不得负偏离）
- 如果发现▲号参数 -> 生成"重要技术参数响应表"（需支撑材料）
- 如果发现#号或演示要求 -> 生成"演示项清单"（标注：需现场演示，不接受PPT）
- 如果发现一般参数 -> 生成"一般技术参数响应表"

**响应策略填充：**
- 对于★项："完全响应，无偏离，提供[证明材料]"
- 对于▲项："优于招标文件要求，具体表现为[USER_INPUT]"
- 对于演示项："已准备现场真实软件演示，演示内容详见技术方案"

### 5. 商务响应章节
**动态内容：**
- 如果发现"交货期/工期" -> 生成工期承诺（照抄招标文件要求，不擅自修改）
- 如果发现"付款方式" -> 生成付款响应（通常填"响应招标文件要求"）
- 如果发现"质保期" -> 生成质保承诺
- 如果发现"履约保证金" -> 生成保函/电汇占位

**偏离表：** 无论是否有偏离，都生成商务偏离表，但至少填一行"无偏离"作为占位

### 6. 方案章节
**条件生成：**
- 如果评分标准中有"项目实施方案"分 -> 生成实施方案章节（人员、进度、安全、应急）
- 如果评分标准中有"售后服务"分 -> 生成售后方案章节（响应时间、技术支持、培训）
- 如果评分标准中有"总体设计方案"分 -> 生成设计方案章节（架构、技术路线）
- 如果评分标准中有"业绩"分 -> 生成业绩表（注意时间范围要求，如"近三年"、"2022年1月至今"）

**分值响应：** 在章节标题后标注"(本章节X分)"，提醒用户重视程度

### 7. 政策章节
**条件生成：**
- 如果招标文件提及"中小企业"、"小微企业" -> 生成《中小企业声明函》模板（注意行业类型填写）
- 如果提及"残疾人福利性单位" -> 生成声明函模板
- 如果提及"节能产品"、"环保产品" -> 生成节能/环保产品报价表模板
- 如果提及"监狱企业" -> 生成监狱企业证明模板

**无政策：** 如果招标文件明确"本项目非专门面向中小企业"且无加分政策，生成备注"本项目不适用政府采购优惠政策"
"""
        
        placeholder_standard = """
## 占位符标准

格式：`[USER_INPUT_描述_单位/格式要求]`

示例：
- `[USER_INPUT_投标总价_人民币万元_保留两位小数]`
- `[USER_INPUT_项目经理姓名_须具备PMP证书]`
- `[USER_INPUT_工期天数_日历日]`
- `[PAGE_NUM_评标索引对应页码]`
- `[CROSS_REF_证明材料编号]`

固定内容标记：`[FIXED_招标文件要求_不可修改]` （如工期、质保期等必须照抄）
"""
        
        quality_check = """
## 质量检查清单
生成模板后，请自检：
- [ ] 是否所有★号参数都有响应表行？
- [ ] 是否所有评分项都有对应章节？
- [ ] 是否有"演示准备"提示（如果存在#号参数）？
- [ ] 人员社保要求（近X个月）是否在人员章节标注？
- [ ] 业绩时间范围（如2022.10至今）是否在业绩表头标注？
"""
        
        prompt = f"""{system_role}

{dynamic_assembly}

{placeholder_standard}

{quality_check}

---

**阶段一分析结果：**

{phase1_result}

---

请基于上述分析结果，生成投标文件模板的完整结构描述。说明每个章节是否生成、包含什么内容、使用什么占位符。输出格式为 Markdown。"""
        
        return prompt
    
    def generate_bid_document(self, template_structure: str, analysis_data: Dict) -> bytes:
        """
        生成最终的投标文件 Word 文档
        返回文档字节流
        """
        # 这里调用文档生成模块
        from app.document_generator import DocumentGenerator
        
        generator = DocumentGenerator()
        return generator.generate(analysis_data)
