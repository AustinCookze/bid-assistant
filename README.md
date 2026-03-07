# 招投标助手 v1.1

智能招标文件分析与投标文件生成工具

## 功能特性

- **招标文件上传**：支持 PDF、DOC、DOCX 格式
- **AI 智能分析**：使用 Kimi K2.5 模型深度分析
  - 废标项清单识别（高/中/低风险分级）
  - 评分标准解析
  - 技术参数提取（★实质性/▲重要/#演示）
  - 商务条款识别
- **投标文件模板生成**：动态生成符合要求的 Word 文档
- **检查清单**：基于分析结果生成核对清单

## 技术栈

### 后端
- FastAPI (Python)
- PyMuPDF + python-docx（文档解析）
- OpenAI SDK（Moonshot API）

### 前端
- React 18 + Vite
- Tailwind CSS
- Axios

## 部署

### Railway 部署

1. 创建 Railway 项目
2. 连接 GitHub 仓库
3. 添加环境变量：
   - `MOONSHOT_API_KEY`: 你的 Moonshot API Key
4. 部署

### 本地开发

```bash
# 后端
cd backend-python
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## API 接口

- `POST /api/upload` - 上传招标文件
- `POST /api/analyze/{id}` - 分析文档
- `GET /api/analysis/{id}` - 获取分析结果
- `GET /api/template/{id}` - 下载投标文件模板

## 版本历史

### v1.1
- Python 后端重构
- 升级到 Kimi K2.5 模型
- 语义分析引擎（TenderDocumentAnalyzer）
- 动态模板生成

### v1.0
- 初始版本（Node.js 后端）
