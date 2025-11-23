"""
Pinecone vector database integration for semantic search.
"""
import os
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
import structlog
from datetime import datetime

logger = structlog.get_logger()


class PineconeStore:
    """Manages vector storage and retrieval in Pinecone."""
    
    NAMESPACES = {
        "slack": "slack/",
        "notion": "notion/",
        "drive": "drive/"
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: str = "knowledge-summarizer",
        dimension: int = 1536,  # text-embedding-3-small dimension
        metric: str = "cosine"
    ):
        """
        Initialize Pinecone store.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Name of the index
            dimension: Vector dimension
            metric: Distance metric (cosine, euclidean, dotproduct)
        """
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.environment = environment or os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric
        
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY must be set")
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        
        # Create or connect to index
        self._init_index()
    
    def _init_index(self):
        """Initialize or connect to Pinecone index."""
        try:
            # Check if index exists
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info("creating_pinecone_index", index_name=self.index_name)
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(
                        cloud='gcp',  # Using GCP
                        region='us-central1'
                    )
                )
                logger.info("pinecone_index_created", index_name=self.index_name)
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            logger.info("connected_to_pinecone_index", index_name=self.index_name)
            
        except Exception as e:
            logger.error("pinecone_init_failed", error=str(e))
            raise
    
    def upsert_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> Dict[str, int]:
        """
        Upsert vectors to Pinecone.
        
        Args:
            vectors: List of embedding vectors
            ids: List of unique IDs for each vector
            metadata: List of metadata dictionaries
            namespace: Namespace to store vectors in
            
        Returns:
            Dictionary with upsert count
        """
        if not vectors or len(vectors) != len(ids) or len(vectors) != len(metadata):
            raise ValueError("Vectors, IDs, and metadata must have same length")
        
        try:
            # Prepare vectors for upsert
            vectors_to_upsert = [
                {
                    "id": vid,
                    "values": vector,
                    "metadata": {
                        **meta,
                        "indexed_at": datetime.utcnow().isoformat()
                    }
                }
                for vid, vector, meta in zip(ids, vectors, metadata)
            ]
            
            # Upsert in batches of 100
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                response = self.index.upsert(
                    vectors=batch,
                    namespace=namespace
                )
                total_upserted += response.upserted_count
            
            logger.info(
                "vectors_upserted",
                count=total_upserted,
                namespace=namespace
            )
            
            return {"upserted_count": total_upserted}
            
        except Exception as e:
            logger.error("vector_upsert_failed", error=str(e), namespace=namespace)
            raise
    
    def query(
        self,
        vector: List[float],
        namespace: str = "default",
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query vectors in Pinecone.
        
        Args:
            vector: Query vector
            namespace: Namespace to query
            top_k: Number of results to return
            filter: Metadata filter
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of matching results with scores and metadata
        """
        try:
            response = self.index.query(
                vector=vector,
                namespace=namespace,
                top_k=top_k,
                filter=filter,
                include_metadata=include_metadata
            )
            
            results = []
            for match in response.matches:
                results.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if include_metadata else {}
                })
            
            logger.info(
                "query_executed",
                namespace=namespace,
                top_k=top_k,
                results_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error("query_failed", error=str(e), namespace=namespace)
            return []
    
    def query_all_namespaces(
        self,
        vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query across all namespaces.
        
        Args:
            vector: Query vector
            top_k: Number of results per namespace
            filter: Metadata filter
            
        Returns:
            Dictionary mapping namespace to results
        """
        all_results = {}
        
        for source, namespace in self.NAMESPACES.items():
            results = self.query(
                vector=vector,
                namespace=namespace,
                top_k=top_k,
                filter=filter
            )
            if results:
                all_results[source] = results
        
        return all_results
    
    def delete_vectors(
        self,
        ids: List[str],
        namespace: str = "default"
    ) -> Dict[str, bool]:
        """
        Delete vectors by ID.
        
        Args:
            ids: List of vector IDs to delete
            namespace: Namespace to delete from
            
        Returns:
            Dictionary with success status
        """
        try:
            self.index.delete(ids=ids, namespace=namespace)
            logger.info("vectors_deleted", count=len(ids), namespace=namespace)
            return {"success": True}
        except Exception as e:
            logger.error("vector_deletion_failed", error=str(e))
            return {"success": False}
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.
        
        Returns:
            Dictionary with index stats
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error("stats_retrieval_failed", error=str(e))
            return {}


if __name__ == "__main__":
    # Test Pinecone connection
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        store = PineconeStore()
        
        # Get stats
        stats = store.get_index_stats()
        print("Pinecone Index Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Test upsert with dummy vector
        test_vector = [0.1] * 1536  # Dummy 1536-dim vector
        test_id = f"test-{datetime.now().timestamp()}"
        test_metadata = {
            "source": "test",
            "content": "This is a test vector",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = store.upsert_vectors(
            vectors=[test_vector],
            ids=[test_id],
            metadata=[test_metadata],
            namespace="slack/"
        )
        print(f"\n✅ Upserted {result['upserted_count']} test vector(s)")
        
        # Test query
        results = store.query(
            vector=test_vector,
            namespace="slack/",
            top_k=1
        )
        print(f"✅ Query returned {len(results)} result(s)")
        
    except Exception as e:
        print(f"❌ Pinecone test failed: {e}")
