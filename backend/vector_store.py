import chromadb
from chromadb import Settings
import boto3
import json
import uuid
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory="./chroma_db", region_name="us-east-1"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="log_pulses",
            metadata={"hnsw:space": "cosine"}
        )
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name
        )
        self.embedding_model_id = "amazon.titan-embed-text-v1"
        # Titan has a 50000 character limit, but we'll use 40000 as a safe margin
        self.max_chars = 40000
        # Rough estimate: 1 token ≈ 4 characters, so 8192 tokens ≈ 32768 characters
        self.max_chars = min(self.max_chars, 8000)  # Conservative limit for token safety

    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within model limits"""
        if len(text) <= self.max_chars:
            return text
        # Truncate and add ellipsis to indicate truncation
        return text[:self.max_chars - 3] + "..."

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text string using AWS Bedrock"""
        try:
            # Truncate text to prevent exceeding model limits
            truncated_text = self._truncate_text(text)
            body = json.dumps({"inputText": truncated_text})
            response = self.bedrock.invoke_model(
                body=body,
                modelId=self.embedding_model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body_stream = response.get("body")
            if not response_body_stream:
                raise ValueError("Empty response body from Bedrock")
            response_body = json.loads(response_body_stream.read())
            embedding = response_body.get("embedding")
            if not embedding:
                raise ValueError("No embedding in Bedrock response")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise e # Propagate error to avoid zero-vectors

    def add_logs(self, logs: List[Dict[str, Any]]):
        """Add batch of logs to the vector database with parallel embedding generation"""
        if not logs:
            return

        from concurrent.futures import ThreadPoolExecutor
        import threading

        # Prepare data for processing
        log_data = []
        for log in logs:
            level = log.get('level', 'INFO')
            message = log.get('message', '')
            correlation_id = log.get('correlationId', 'UNKNOWN')
            user_id = log.get('userId', '')
            
            embedding_content = f"[{level}] {message}"
            if user_id:
                embedding_content += f" | User: {user_id}"
            if correlation_id and correlation_id != 'UNKNOWN':
                embedding_content += f" | Trace: {correlation_id}"
            
            content = f"[{level}] {message}"
            if user_id:
                content += f" | User: {user_id}"
                
            log_data.append({
                'log': log,
                'embedding_content': embedding_content,
                'document_content': content
            })

        documents = []
        metadatas = []
        ids = []
        embeddings = []

        # Process embeddings in parallel (max 10 concurrent requests to Bedrock)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map the _get_embedding function over the content
            results = list(executor.map(
                lambda d: (d, self._get_embedding(d['embedding_content'])), 
                log_data
            ))

        for data, emb in results:
            if emb:
                log = data['log']
                embeddings.append(emb)
                documents.append(data['document_content'])
                metadatas.append({
                    "timestamp": int(log.get("epoch", 0)),
                    "level": log.get("level", "INFO"),
                    "correlationId": log.get("correlationId", "UNKNOWN"),
                    "isError": str(log.get("isError", False)),
                    "raw_json": json.dumps(log)
                })
                ids.append(str(uuid.uuid4()))

        if embeddings:
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Stored {len(embeddings)} logs in VectorDB.")
            # Auto-prune to prevent unbounded disk growth
            self._prune_if_needed()

    MAX_COLLECTION_SIZE = 50000  # Maximum number of log entries to keep

    def _prune_if_needed(self):
        """Delete oldest entries if collection exceeds MAX_COLLECTION_SIZE."""
        try:
            total = self.collection.count()
            if total <= self.MAX_COLLECTION_SIZE:
                return
            
            to_delete_count = total - self.MAX_COLLECTION_SIZE
            logger.info(f"Collection has {total} entries, pruning {to_delete_count} oldest records...")
            
            # Fetch only IDs and timestamps to save memory
            # Note: We still fetch all to find the oldest. 
            # Optimization: If total is very large, this could be slow.
            results = self.collection.get(include=["metadatas"])
            
            if not results or not results["ids"]:
                return

            # Extract IDs and timestamps
            items = []
            for i, metadata in enumerate(results["metadatas"]):
                items.append({
                    "id": results["ids"][i],
                    "timestamp": metadata.get("timestamp", 0)
                })
            
            # Sort by timestamp ascending (oldest first)
            items.sort(key=lambda x: x["timestamp"])
            
            ids_to_delete = [item["id"] for item in items[:to_delete_count]]

            # Delete in batches
            batch_size = 1000
            for i in range(0, len(ids_to_delete), batch_size):
                self.collection.delete(ids=ids_to_delete[i:i+batch_size])

            logger.info(f"Pruned {len(ids_to_delete)} records. Remaining: {self.collection.count()}")
        except Exception as e:
            logger.error(f"Error during auto-pruning: {e}", exc_info=True)

    def search_similar_logs(self, query: str, n_results: int = 5, start_time: int = None, end_time: int = None) -> List[Dict[str, Any]]:
        """Search for semantically similar logs with optional time filter"""
        # Truncate query to prevent exceeding model limits
        truncated_query = self._truncate_text(query)
        query_embedding = self._get_embedding(truncated_query)
        
        where = {}
        if start_time and end_time:
            where = {
                "$and": [
                    {"timestamp": {"$gte": start_time}},
                    {"timestamp": {"$lte": end_time}}
                ]
            }
        elif start_time:
            where = {"timestamp": {"$gte": start_time}}
        elif end_time:
            where = {"timestamp": {"$lte": end_time}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where if where else None
        )

        found_logs = []
        if results and results['metadatas']:
            for meta in results['metadatas'][0]:
                found_logs.append(json.loads(meta['raw_json']))
        
        return found_logs

    def get_recent_logs(self, limit: int = 10000) -> List[Dict[str, Any]]:
        """Retrieve most recent logs from the collection"""
        # ChromaDB doesn't support complex sorting on all metadata easily without full retrieval
        # but for recent logs, we can just get the most recently added or use metadata if small enough.
        # For simplicity in this implementation, we'll get the last 'limit' items.
        results = self.collection.get(
            limit=limit,
            include=['metadatas']
        )
        
        logs = []
        if results and results['metadatas']:
            for meta in results['metadatas']:
                logs.append(json.loads(meta['raw_json']))
        
        # Sort desc by timestamp
        logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return logs[:limit]

    def get_logs_in_range(self, start_time: int, end_time: int, limit: int = 5000) -> List[Dict[str, Any]]:
        """Retrieve logs within a specific timestamp range from ChromaDB"""
        results = self.collection.get(
            where={
                "$and": [
                    {"timestamp": {"$gte": start_time}},
                    {"timestamp": {"$lte": end_time}}
                ]
            },
            limit=limit,
            include=['metadatas']
        )
        
        logs = []
        if results and results['metadatas']:
            for meta in results['metadatas']:
                logs.append(json.loads(meta['raw_json']))
        
        # Sort desc
        logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return logs

    def get_logs_by_correlation_id(self, correlation_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve all logs belonging to a specific correlation ID from ChromaDB"""
        results = self.collection.get(
            where={"correlationId": correlation_id},
            limit=limit,
            include=['metadatas']
        )
        
        logs = []
        if results and results['metadatas']:
            for meta in results['metadatas']:
                logs.append(json.loads(meta['raw_json']))
        
        # Sort asc for trace flow (usually wanted chronological)
        logs.sort(key=lambda x: x.get('timestamp', 0))
        return logs
