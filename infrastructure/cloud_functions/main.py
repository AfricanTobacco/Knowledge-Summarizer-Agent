"""
GCP Cloud Functions for Knowledge Summarizer Agent.
These functions handle ingestion, embedding, and query processing.
"""

# Ingest Function - triggers on Pub/Sub messages from Slack/Notion/Drive
def ingest_function(event, context):
    """
    Cloud Function triggered by Pub/Sub for ingestion events.
    
    Args:
        event: Pub/Sub event data
        context: Event context
    """
    import base64
    import json
    import os
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from processing.chunker import ContentChunker
    from processing.pii_redactor import PIIRedactor
    from processing.embedder import Embedder
    from storage.pinecone_store import PineconeStore
    import structlog
    
    logger = structlog.get_logger()
    
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        message_data = json.loads(pubsub_message)
        
        logger.info("ingestion_started", source=message_data.get("source"))
        
        # Extract data
        source = message_data.get("source")  # slack, notion, or drive
        content = message_data.get("content")
        metadata = message_data.get("metadata", {})
        
        # Initialize components
        chunker = ContentChunker()
        redactor = PIIRedactor(enabled=True)
        embedder = Embedder()
        vector_store = PineconeStore()
        
        # Redact PII
        redaction_result = redactor.redact(content)
        clean_content = redaction_result.redacted_text
        
        # Chunk content
        chunks = chunker.chunk_document(
            content=clean_content,
            source=source,
            source_id=metadata.get("id"),
            author=metadata.get("author"),
            timestamp=metadata.get("timestamp"),
            url=metadata.get("url"),
            additional_metadata=metadata
        )
        
        # Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embedding_results = embedder.embed_batch(texts)
        
        # Prepare for Pinecone
        vectors = []
        ids = []
        chunk_metadata = []
        
        for chunk, embedding_result in zip(chunks, embedding_results):
            if embedding_result:
                vectors.append(embedding_result.vector)
                ids.append(f"{source}-{metadata.get('id')}-{chunk.chunk_index}")
                chunk_metadata.append({
                    **chunk.metadata,
                    "content": chunk.content[:1000],  # Store preview
                    "model": embedding_result.model
                })
        
        # Upsert to Pinecone
        if vectors:
            namespace = vector_store.NAMESPACES.get(source, "default")
            result = vector_store.upsert_vectors(
                vectors=vectors,
                ids=ids,
                metadata=chunk_metadata,
                namespace=namespace
            )
            
            logger.info(
                "ingestion_completed",
                source=source,
                chunks=len(chunks),
                vectors_upserted=result.get("upserted_count", 0)
            )
        
        return {"status": "success", "chunks_processed": len(chunks)}
        
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        return {"status": "error", "message": str(e)}


# Embed Function - for on-demand embedding generation
def embed_function(request):
    """
    HTTP Cloud Function for on-demand embedding generation.
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with embeddings
    """
    import json
    import os
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from processing.embedder import Embedder
    import structlog
    
    logger = structlog.get_logger()
    
    try:
        request_json = request.get_json()
        texts = request_json.get("texts", [])
        
        if not texts:
            return {"error": "No texts provided"}, 400
        
        embedder = Embedder()
        results = embedder.embed_batch(texts)
        
        embeddings = [
            {
                "vector": result.vector if result else None,
                "token_count": result.token_count if result else 0,
                "cost_usd": result.cost_usd if result else 0
            }
            for result in results
        ]
        
        cost_summary = embedder.get_cost_summary()
        
        return {
            "embeddings": embeddings,
            "cost_summary": cost_summary
        }
        
    except Exception as e:
        logger.error("embed_function_failed", error=str(e))
        return {"error": str(e)}, 500


# Query Function - handles search queries
def query_function(request):
    """
    HTTP Cloud Function for semantic search queries.
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with search results
    """
    import json
    import os
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from processing.embedder import Embedder
    from storage.pinecone_store import PineconeStore
    import structlog
    
    logger = structlog.get_logger()
    
    try:
        request_json = request.get_json()
        query_text = request_json.get("query")
        top_k = request_json.get("top_k", 5)
        namespace = request_json.get("namespace", "all")
        
        if not query_text:
            return {"error": "No query provided"}, 400
        
        # Generate query embedding
        embedder = Embedder()
        embedding_result = embedder.embed_text(query_text)
        
        if not embedding_result:
            return {"error": "Failed to generate embedding"}, 500
        
        # Search Pinecone
        vector_store = PineconeStore()
        
        if namespace == "all":
            results = vector_store.query_all_namespaces(
                vector=embedding_result.vector,
                top_k=top_k
            )
        else:
            results = {
                namespace: vector_store.query(
                    vector=embedding_result.vector,
                    namespace=namespace,
                    top_k=top_k
                )
            }
        
        return {
            "query": query_text,
            "results": results,
            "token_count": embedding_result.token_count
        }
        
    except Exception as e:
        logger.error("query_function_failed", error=str(e))
        return {"error": str(e)}, 500
