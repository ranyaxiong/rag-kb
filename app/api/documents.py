"""
文档管理API
"""
import logging
import os
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import VectorStore
from app.models.schemas import Document, ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局实例（延迟初始化）
doc_processor = DocumentProcessor()
vector_store = None

def get_vector_store():
    """获取向量存储实例（延迟初始化）"""
    global vector_store
    if vector_store is None:
        vector_store = VectorStore()
    return vector_store


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """上传文档"""
    try:
        # 检查文件类型
        if not doc_processor.is_supported_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {list(doc_processor.supported_extensions)}"
            )
        
        # 检查文件大小（限制10MB）
        file_content = await file.read()
        if len(file_content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 100MB."
            )
        
        # 检查是否为重复文件（基于文件名和大小）
        existing_docs = get_vector_store().list_documents()
        for doc in existing_docs:
            if doc['filename'] == file.filename:
                raise HTTPException(
                    status_code=409,
                    detail=f"Document '{file.filename}' already exists. Please delete the existing document first or rename your file."
                )
        
        # 保存文件
        file_path = doc_processor.save_uploaded_file(file_content, file.filename)
        
        # 获取文件基本信息
        file_info = doc_processor.get_document_info(file_path)
        if not file_info:
            raise HTTPException(status_code=500, detail="Failed to get file information")
        
        # 创建文档记录
        doc_record = Document(
            id=os.path.basename(file_path).split('_')[0],
            filename=file.filename,
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            upload_time=datetime.now(),
            status="processing",
            chunk_count=None
        )
        
        # 后台处理文档
        background_tasks.add_task(
            process_document_background,
            file_path,
            file.filename
        )
        
        return {
            "success": True,
            "message": "File uploaded successfully and processing started",
            "document": doc_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_document_background(file_path: str, filename: str):
    """后台处理文档"""
    try:
        logger.info(f"Processing document: {filename}")
        
        # 处理文档
        result = doc_processor.process_document(file_path, filename)
        
        if result['status'] == 'completed':
            # 添加到向量存储
            get_vector_store().add_documents(result['chunks'])
            logger.info(f"Document {filename} processed successfully")
        else:
            logger.error(f"Document processing failed: {result.get('error_message')}")
            
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")


@router.get("/", response_model=List[Document])
async def list_documents():
    """获取文档列表"""
    try:
        documents = get_vector_store().list_documents()
        
        # 转换为Document模型
        doc_list = []
        for doc_info in documents:
            doc = Document(
                id=doc_info['document_id'],
                filename=doc_info['filename'],
                file_type=os.path.splitext(doc_info['filename'])[1],
                file_size=0,  # 这里我们没有存储文件大小信息
                upload_time=datetime.fromisoformat(doc_info['processed_at']) if doc_info.get('processed_at') else datetime.now(),
                status="completed",
                chunk_count=doc_info['chunk_count']
            )
            doc_list.append(doc)
        
        return doc_list
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/{document_id}")
async def get_document(document_id: str):
    """获取文档详情"""
    try:
        documents = get_vector_store().list_documents()
        
        # 查找指定文档
        doc_info = None
        for doc in documents:
            if doc['document_id'] == document_id:
                doc_info = doc
                break
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "document": doc_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """删除文档"""
    try:
        # 从向量存储中删除
        success = get_vector_store().delete_document_by_id(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "message": f"Document {document_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post("/batch-upload")
async def batch_upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """批量上传文档"""
    try:
        if len(files) > 10:
            raise HTTPException(
                status_code=400,
                detail="Too many files. Maximum is 10 files per batch."
            )
        
        results = []
        
        for file in files:
            try:
                # 检查文件类型
                if not doc_processor.is_supported_file(file.filename):
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"Unsupported file type"
                    })
                    continue
                
                # 检查是否为重复文件
                existing_docs = get_vector_store().list_documents()
                file_exists = any(doc['filename'] == file.filename for doc in existing_docs)
                if file_exists:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"Document already exists"
                    })
                    continue
                
                # 保存文件
                file_content = await file.read()
                file_path = doc_processor.save_uploaded_file(file_content, file.filename)
                
                # 后台处理
                background_tasks.add_task(
                    process_document_background,
                    file_path,
                    file.filename
                )
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "message": "Upload successful, processing started"
                })
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Processed {len(files)} files",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


@router.get("/stats/overview")
async def get_stats():
    """获取文档统计信息"""
    try:
        collection_info = get_vector_store().get_collection_info()
        documents = get_vector_store().list_documents()
        
        stats = {
            "total_documents": len(documents),
            "total_chunks": collection_info.get("document_count", 0),
            "supported_formats": list(doc_processor.supported_extensions),
            "storage_info": {
                "upload_dir": settings.upload_dir,
                "chroma_db_path": settings.chroma_db_path
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")