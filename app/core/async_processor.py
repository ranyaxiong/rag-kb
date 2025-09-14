import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AsyncDocumentProcessor:
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="doc_processor"
        )
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # 启动清理线程
        self._start_cleanup_thread()
    
    def submit_task(self, document_id: str, file_path: str, filename: str) -> str:
        """提交处理任务"""
        future = self.executor.submit(
            self._process_document_safe,
            document_id, file_path, filename
        )
        
        with self._lock:
            self.tasks[document_id] = {
                "future": future,
                "filename": filename,
                "submitted_at": time.time(),
                "status": "queued"
            }
        
        logger.info(f"Task submitted for document {filename} (ID: {document_id})")
        return document_id
    
    def get_task_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self._lock:
            task_info = self.tasks.get(document_id)
            
        if not task_info:
            return None
            
        future = task_info["future"]
        
        if future.done():
            if future.exception():
                return {
                    "status": "failed",
                    "error": str(future.exception()),
                    "filename": task_info["filename"]
                }
            else:
                result = future.result()
                return {
                    "status": "completed" if result.get("success") else "failed",
                    "filename": task_info["filename"],
                    **result
                }
        else:
            return {
                "status": "processing",
                "filename": task_info["filename"],
                "submitted_at": task_info["submitted_at"]
            }
    
    def _process_document_safe(self, document_id: str, file_path: str, filename: str) -> Dict[str, Any]:
        """安全的文档处理包装器"""
        try:
            from app.core.document_processor import doc_processor
            from app.core.vector_store import get_vector_store
            from app.core.job_status import job_status
            
            logger.info(f"Starting processing for {filename}")
            
            # 更新状态
            job_status.mark_processing(document_id, progress=10, message="开始处理文档")
            
            # 移动文件到最终目录
            if doc_processor.is_in_temp_dir(file_path):
                real_path = doc_processor.move_to_upload_dir(file_path, filename)
            else:
                real_path = file_path
            
            job_status.mark_processing(document_id, progress=20, message="文件准备完成")
            
            # 处理文档
            result = doc_processor.process_document(real_path, filename)
            
            if result['status'] == 'completed':
                # 添加到向量存储
                chunks = result.get('chunks', [])
                for chunk in chunks:
                    chunk.metadata['async_document_id'] = document_id
                
                job_status.mark_processing(document_id, progress=80, message="生成向量嵌入")
                get_vector_store().add_documents(chunks)
                
                # 标记完成
                job_status.mark_completed(
                    document_id,
                    chunk_count=len(chunks),
                    filename=filename
                )
                
                logger.info(f"Document {filename} processed successfully")
                return {
                    "success": True,
                    "chunk_count": len(chunks),
                    "document_id": document_id
                }
            else:
                error_msg = result.get('error_message', 'Unknown processing error')
                job_status.mark_failed(document_id, error=error_msg, filename=filename)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Document processing failed for {filename}: {str(e)}")
            job_status.mark_failed(document_id, error=str(e), filename=filename)
            return {"success": False, "error": str(e)}
    
    def _start_cleanup_thread(self):
        """启动清理线程，定期清理完成的任务"""
        def cleanup_worker():
            while True:
                try:
                    current_time = time.time()
                    with self._lock:
                        # 清理1小时前完成的任务
                        to_remove = []
                        for doc_id, task_info in self.tasks.items():
                            if (task_info["future"].done() and 
                                current_time - task_info["submitted_at"] > 3600):
                                to_remove.append(doc_id)
                        
                        for doc_id in to_remove:
                            del self.tasks[doc_id]
                            
                    if to_remove:
                        logger.info(f"Cleaned up {len(to_remove)} completed tasks")
                        
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
                
                time.sleep(300)  # 5分钟清理一次
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

# 全局单例
async_processor = AsyncDocumentProcessor(max_workers=2)