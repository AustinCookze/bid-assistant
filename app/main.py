"""
FastAPI 主应用 - 内存存储版本（适配 Railway 无状态部署）
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import uuid
import json
import io
from datetime import datetime

from app.config import get_settings
from app.document_parser import DocumentParser, TextCleaner
from app.analyzer import TenderDocumentAnalyzer
from app.ai_service import AIService
from app.document_generator import DocumentGenerator


app = FastAPI(
    title="招投标助手 v1.1",
    description="智能招标文件分析与投标文件生成",
    version="1.1.0"
)

# CORS 配置
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存存储（适配 Railway 无状态部署）
analysis_results = {}
file_storage = {}  # 文件内容内存存储

# API 配置存储（支持运行时修改）
api_config = {
    "api_key": settings.MOONSHOT_API_KEY,
    "model_name": settings.MODEL_NAME,
    "base_url": settings.MODEL_BASE_URL
}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "1.1.0",
        "model": api_config["model_name"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/config")
async def get_config():
    """
    获取当前 API 配置
    返回模型名称和 API 基础配置（不包含敏感信息）
    """
    return {
        "model_name": api_config["model_name"],
        "base_url": api_config["base_url"],
        "available_models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot 8K", "context": "8K"},
            {"id": "moonshot-v1-32k", "name": "Moonshot 32K", "context": "32K"},
            {"id": "moonshot-v1-128k", "name": "Moonshot 128K", "context": "128K"},
            {"id": "kimi-k2.5", "name": "Kimi K2.5", "context": "256K"}
        ]
    }


@app.post("/api/config")
async def update_config(config: dict):
    """
    更新 API 配置
    支持修改：api_key, model_name, base_url
    """
    global api_config
    
    # 验证必填字段
    if "api_key" not in config or not config["api_key"]:
        raise HTTPException(status_code=400, detail="API Key 不能为空")
    
    if "model_name" not in config or not config["model_name"]:
        raise HTTPException(status_code=400, detail="模型名称不能为空")
    
    # 验证支持的模型
    supported_models = ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-k2.5"]
    if config["model_name"] not in supported_models:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的模型: {config['model_name']}。支持的模型: {', '.join(supported_models)}"
        )
    
    # 更新配置
    api_config["api_key"] = config["api_key"]
    api_config["model_name"] = config["model_name"]
    
    if "base_url" in config and config["base_url"]:
        api_config["base_url"] = config["base_url"]
    
    return {
        "message": "配置更新成功",
        "model_name": api_config["model_name"],
        "base_url": api_config["base_url"]
    }


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传招标文件（内存存储版本）
    支持格式：PDF, DOCX, DOC
    """
    # 验证文件类型
    allowed_extensions = {'.pdf', '.docx', '.doc'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。仅支持 PDF, DOCX, DOC"
        )
    
    # 生成唯一 ID
    file_id = str(uuid.uuid4())
    
    try:
        # 读取文件内容到内存
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # 保存到内存
        file_storage[file_id] = {
            "content": content,
            "filename": file.filename,
            "ext": file_ext
        }
        
        # 解析文档（从内存）
        parser = DocumentParser()
        raw_text = parser.parse_from_bytes(content, file_ext.replace('.', ''))
        
        # 清洗文本
        cleaner = TextCleaner()
        clean_text = cleaner.clean(raw_text)
        
        # 保存解析结果
        analysis_results[file_id] = {
            "id": file_id,
            "filename": file.filename,
            "text": clean_text,
            "status": "parsed",
            "created_at": datetime.now().isoformat(),
            "analysis": None,
            "template": None
        }
        
        return {
            "id": file_id,
            "filename": file.filename,
            "status": "parsed",
            "text_length": len(clean_text),
            "message": "文件上传成功，请调用分析接口"
        }
        
    except Exception as e:
        # 清理内存
        if file_id in file_storage:
            del file_storage[file_id]
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@app.post("/api/analyze/{file_id}")
async def analyze_document(file_id: str, background_tasks: BackgroundTasks):
    """
    分析招标文件
    使用 AI 进行深度分析
    """
    if file_id not in analysis_results:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    result = analysis_results[file_id]
    
    if result["status"] == "analyzing":
        return {"status": "analyzing", "message": "分析进行中，请稍后"}
    
    if result["analysis"] is not None:
        return {
            "status": "completed",
            "analysis": result["analysis"],
            "message": "分析已完成"
        }
    
    try:
        result["status"] = "analyzing"
        
        # 阶段一：语义分析
        analyzer = TenderDocumentAnalyzer()
        preliminary_analysis = analyzer.analyze(result["text"])
        
        # 阶段二：AI 深度分析
        ai_service = AIService()
        ai_result = ai_service.analyze_tender_document(result["text"])
        
        # 合并结果
        analysis_data = {
            "id": file_id,
            "project_info": preliminary_analysis.project_info,
            "disqualification_items": [
                {
                    "category": item.category,
                    "content": item.content,
                    "risk_level": item.risk_level,
                    "source": item.source
                }
                for item in preliminary_analysis.disqualification_items
            ],
            "scoring_criteria": [
                {
                    "category": item.category,
                    "factor": item.factor,
                    "score": item.score,
                    "criteria": item.criteria,
                    "proof_required": item.proof_required
                }
                for item in preliminary_analysis.scoring_criteria
            ],
            "business_terms": {
                "delivery_time": next((t.content for t in preliminary_analysis.business_terms 
                                      if t.term_type == "时间"), ""),
                "payment_terms": "",
                "warranty_period": "",
                "bid_bond": "",
                "performance_bond": ""
            },
            "technical_requirements": [
                {
                    "param_id": req.param_id,
                    "param_name": req.param_name,
                    "requirement": req.requirement,
                    "is_essential": req.is_essential,
                    "is_demo": req.is_demo,
                    "is_important": req.is_important,
                    "proof_required": req.proof_required
                }
                for req in preliminary_analysis.technical_requirements
            ],
            "notes": preliminary_analysis.notes,
            "checklists": preliminary_analysis.checklists,
            "ai_analysis": ai_result.get("analysis", ""),
            "template_structure": ai_result.get("template_structure", "")
        }
        
        result["analysis"] = analysis_data
        result["status"] = "analyzed"
        
        return {
            "status": "completed",
            "analysis": analysis_data,
            "message": "分析完成"
        }
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.get("/api/analysis/{file_id}")
async def get_analysis(file_id: str):
    """获取分析结果"""
    if file_id not in analysis_results:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    result = analysis_results[file_id]
    
    return {
        "id": file_id,
        "status": result["status"],
        "filename": result["filename"],
        "analysis": result.get("analysis"),
        "created_at": result["created_at"]
    }


@app.get("/api/template/{file_id}")
async def download_template(file_id: str):
    """
    下载投标文件模板
    生成 Word 文档
    """
    if file_id not in analysis_results:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    result = analysis_results[file_id]
    
    if not result.get("analysis"):
        raise HTTPException(status_code=400, detail="请先完成分析")
    
    try:
        # 生成文档
        generator = DocumentGenerator()
        doc_bytes = generator.generate(result["analysis"])
        
        # 返回文件
        filename = f"投标文件模板_{result['filename'].split('.')[0]}.docx"
        
        return StreamingResponse(
            io.BytesIO(doc_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成模板失败: {str(e)}")


@app.get("/api/analysis/{file_id}/json")
async def download_analysis_json(file_id: str):
    """下载分析结果 JSON"""
    if file_id not in analysis_results:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    result = analysis_results[file_id]
    
    if not result.get("analysis"):
        raise HTTPException(status_code=400, detail="请先完成分析")
    
    return StreamingResponse(
        io.BytesIO(json.dumps(result["analysis"], ensure_ascii=False, indent=2).encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=分析结果_{file_id}.json"}
    )


@app.delete("/api/analysis/{file_id}")
async def delete_analysis(file_id: str):
    """删除分析记录"""
    if file_id not in analysis_results:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 清理内存
    if file_id in file_storage:
        del file_storage[file_id]
    del analysis_results[file_id]
    
    return {"message": "删除成功"}
