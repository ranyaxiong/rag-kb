"""
文档管理API
"""
import logging
import os
import uuid
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import VectorStore
from app.models.schemas import Document, ApiResponse
from app.core.job_status import job_status
from app.core.async_processor import async_processor

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


@router.post("/upload-async")
async def upload_document_async(file: UploadFile = File(...)):
    """真正的异步上传（线程池版本）"""
    try:
        # 验证文件...
        
        # 保存到临时目录
        file_content = await file.read()
        temp_path = doc_processor.save_to_temp_file(file_content, file.filename)
        
        # 生成文档ID
        document_id = str(uuid.uuid4())
        
        # 初始化作业状态
        job_status.init_job(document_id, file.filename, {
            "processing_mode": "async_thread",
            "stage": "queued"
        })
        
        # 提交到线程池（立即返回）
        async_processor.submit_task(document_id, temp_path, file.filename)
        
        return {
            "success": True,
            "message": "文件上传成功，已加入处理队列",
            "document_id": document_id,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    async_processing: bool = False  # 保持原有同步处理作为选项
):
    """上传文档（兼容原有接口）"""
    try:
        # 检查文件类型
        if not doc_processor.is_supported_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {list(doc_processor.supported_extensions)}"
            )
        
        # 检查文件大小
        file_content = await file.read()
        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        if len(file_content) > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File size too large. Maximum size is {settings.max_file_size_mb}MB."
            )
        
        # 高效重复检查（按文件名）
        if get_vector_store().document_exists_by_filename(file.filename):
            raise HTTPException(
                status_code=409,
                detail=f"Document '{file.filename}' already exists. Please delete the existing document first or rename your file."
            )
        
        # 保存文件（同步路径使用最终目录，兼容现有测试与逻辑）
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
        
        if async_processing:
            # 异步处理：立即返回，后台处理
            # 异步处理使用临时目录写入，后台搬迁
            temp_path = doc_processor.save_to_temp_file(file_content, file.filename)
            # 生成document_id并初始化作业
            import uuid
            async_document_id = str(uuid.uuid4())
            try:
                job_status.init_job(async_document_id, file.filename, {
                    "processing_mode": "async",
                    "stage": "uploaded"
                })
            except Exception:
                pass
            background_tasks.add_task(
                process_document_background,
                temp_path,
                file.filename,
                async_document_id
            )
            
            return {
                "success": True,
                "message": "File uploaded successfully and processing started in background",
                "document": doc_record,
                "document_id": async_document_id,
                "processing_mode": "async"
            }
        else:
            # 同步处理：等待完成后返回
            logger.info(f"Processing document: {file.filename}")
            result = doc_processor.process_document(file_path, file.filename)
            
            if result['status'] == 'completed':
                # 添加到向量存储
                get_vector_store().add_documents(result['chunks'])
                doc_record.status = "completed"
                doc_record.chunk_count = result['chunk_count']
                logger.info(f"Document {file.filename} processed successfully")
                
                return {
                    "success": True,
                    "message": "File uploaded and processed successfully",
                    "document": doc_record,
                    "document_id": result['document_id'],
                    "chunk_count": result['chunk_count'],
                    "status": result['status'],
                    "processing_mode": "sync"
                }
            else:
                doc_record.status = "failed"
                logger.error(f"Document processing failed: {result.get('error_message')}")
                return {
                    "success": False,
                    "message": f"Document processing failed: {result.get('error_message')}",
                    "document": doc_record,
                    "processing_mode": "sync"
                }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_document_background(file_path: str, filename: str, document_id: str = None):
    """后台处理文档"""
    try:
        logger.info(f"Processing document: {filename} (ID: {document_id})")
        try:
            if document_id:
                job_status.mark_processing(document_id, progress=1, message="Job started")
        except Exception:
            pass
        
        # 如果路径位于临时目录，先搬迁到最终上传目录
        try:
            if doc_processor.is_in_temp_dir(file_path):
                real_path = doc_processor.move_to_upload_dir(file_path, filename)
            else:
                real_path = file_path
            try:
                if document_id:
                    job_status.mark_processing(document_id, progress=10, message="File moved to upload dir", file_path=real_path)
            except Exception:
                pass
        except Exception as move_err:
            logger.error(f"Failed to move temp file before processing: {move_err}")
            real_path = file_path

        # 处理文档
        try:
            if document_id:
                job_status.mark_processing(document_id, progress=15, message="Processing document")
        except Exception:
            pass
        result = doc_processor.process_document(real_path, filename)
        
        if result['status'] == 'completed':
            # 添加document_id到chunks元数据
            if document_id:
                for chunk in result['chunks']:
                    chunk.metadata['async_document_id'] = document_id
            
            # 添加到向量存储
            get_vector_store().add_documents(result['chunks'])
            logger.info(f"Document {filename} processed successfully (ID: {document_id})")
            try:
                if document_id:
                    job_status.mark_completed(
                        document_id,
                        chunk_count=result.get('chunk_count', 0),
                        filename=filename,
                        processed_at=datetime.now().isoformat()
                    )
            except Exception:
                pass
        else:
            logger.error(f"Document processing failed (ID: {document_id}): {result.get('error_message')}")
            try:
                if document_id:
                    job_status.mark_failed(document_id, error=result.get('error_message', 'Unknown error'), filename=filename)
            except Exception:
                pass
            
    except Exception as e:
        logger.error(f"Error in background processing (ID: {document_id}): {str(e)}")
        try:
            if document_id:
                job_status.mark_failed(document_id, error=str(e), filename=filename)
        except Exception:
            pass


@router.get("/status/{document_id}")
async def get_processing_status(document_id: str):
    """获取处理状态（线程池版本）"""
    try:
        # 先检查线程池状态
        thread_status = async_processor.get_task_status(document_id)
        if thread_status:
            return thread_status
        
        # 回退到job_status检查
        status_info = job_status.get_job_status(document_id)
        if not status_info:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return status_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/stream/{document_id}")
async def stream_processing_status(document_id: str):
    """SSE流式状态推送"""
    async def event_generator():
        try:
            retry_count = 0
            max_retries = 200  # 最多重试200次（5分钟），适应大型扫描版PDF的OCR处理

            while retry_count < max_retries:
                # 复用现有状态查询逻辑
                status = async_processor.get_task_status(document_id)
                if not status:
                    status = job_status.get_job_status(document_id)

                if status:
                    yield f"data: {json.dumps(status)}\n\n"

                    # 处理完成或失败时结束流
                    if status.get("status") in ["completed", "failed"]:
                        break
                else:
                    # 如果找不到状态，可能是刚提交还没开始处理，继续等待
                    yield f"data: {json.dumps({'status': 'waiting', 'message': 'Waiting for processing to start...'})}\n\n"

                await asyncio.sleep(1.5)  # 1.5秒轮询间隔
                retry_count += 1

            # 超时后发送超时状态
            if retry_count >= max_retries:
                yield f"data: {json.dumps({'status': 'timeout', 'message': 'Status check timeout'})}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error for document {document_id}: {str(e)}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )


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
                
                # 高效重复检查（按文件名）
                if get_vector_store().document_exists_by_filename(file.filename):
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"Document already exists"
                    })
                    continue
                
                # 保存到临时目录，后台搬迁再处理
                file_content = await file.read()
                temp_path = doc_processor.save_to_temp_file(file_content, file.filename)
                
                # 后台处理
                background_tasks.add_task(
                    process_document_background,
                    temp_path,
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
        
        # 检查OCR能力（若缺少依赖则降级）
        ocr_available = False
        image_processing_available = False
        enhanced_pdf_processing = False
        try:
            from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
            pdf_processor = EnhancedPDFProcessor()
            ocr_available = getattr(pdf_processor, 'ocr_available', False)
            image_processing_available = getattr(pdf_processor, 'image_extraction_available', False)
            enhanced_pdf_processing = True
        except Exception as e:
            logger.warning(f"Enhanced PDF processor unavailable: {e}")

        stats = {
            "total_documents": len(documents),
            "total_chunks": collection_info.get("document_count", 0),
            "supported_formats": list(doc_processor.supported_extensions),
            "processing_capabilities": {
                "ocr_available": ocr_available,
                "image_processing_available": image_processing_available,
                "enhanced_pdf_processing": enhanced_pdf_processing
            },
            "storage_info": {
                "upload_dir": settings.upload_dir,
                "chroma_db_path": settings.chroma_db_path,
                "max_file_size_mb": settings.max_file_size_mb
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/pdf-info/{document_id}")
async def get_pdf_info(document_id: str):
    """获取PDF文档的详细分析信息"""
    try:
        # 查找文档
        documents = get_vector_store().list_documents()
        doc_info = None
        for doc in documents:
            if doc['document_id'] == document_id:
                doc_info = doc
                break
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 如果是PDF文档，提供详细分析
        filename = doc_info.get('filename', '')
        if filename.lower().endswith('.pdf'):
            # 尝试找到文件路径（这里简化处理，实际可能需要更复杂的查找逻辑）
            file_path = doc_info.get('file_path')
            if not (file_path and os.path.exists(file_path)):
                return {
                    "success": False,
                    "message": "PDF文件路径未找到或文件已移动"
                }
            try:
                from app.core.enhanced_pdf_processor import EnhancedPDFProcessor
                pdf_processor = EnhancedPDFProcessor()
                processing_info = pdf_processor.get_processing_info(file_path)
                return {
                    "success": True,
                    "document_id": document_id,
                    "filename": filename,
                    "processing_info": processing_info
                }
            except Exception as e:
                logger.warning(f"Enhanced PDF analysis unavailable: {e}")
                return {
                    "success": False,
                    "message": "增强型PDF分析不可用（缺少依赖或处理器不可用）"
                }
        else:
            return {
                "success": False,
                "message": "该文档不是PDF格式"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF info for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDF info: {str(e)}")

