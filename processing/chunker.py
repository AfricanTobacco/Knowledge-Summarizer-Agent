"""
Content chunking module for splitting documents into embeddable segments.
"""
import tiktoken
from typing import List, Dict, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class Chunk:
    """Represents a chunk of content with metadata."""
    content: str
    metadata: Dict[str, Any]
    token_count: int
    chunk_index: int


class ContentChunker:
    """Chunks content into token-sized segments with overlap."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        overlap_size: int = 50,
        encoding_name: str = "cl100k_base"  # GPT-4/turbo encoding
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target size for each chunk in tokens
            overlap_size: Number of overlapping tokens between chunks
            encoding_name: Tokenizer encoding to use
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.encoding = tiktoken.get_encoding(encoding_name)
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text content to chunk
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            logger.warning("empty_text_provided_for_chunking")
            return []
        
        metadata = metadata or {}
        
        # Encode the entire text
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        if total_tokens <= self.chunk_size:
            # Text fits in single chunk
            return [Chunk(
                content=text,
                metadata=metadata,
                token_count=total_tokens,
                chunk_index=0
            )]
        
        chunks = []
        start_idx = 0
        chunk_idx = 0
        
        while start_idx < total_tokens:
            # Calculate end index for this chunk
            end_idx = min(start_idx + self.chunk_size, total_tokens)
            
            # Extract chunk tokens and decode
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk with metadata
            chunk = Chunk(
                content=chunk_text,
                metadata={
                    **metadata,
                    "chunk_index": chunk_idx,
                    "total_chunks": None,  # Will be set after all chunks created
                    "start_token": start_idx,
                    "end_token": end_idx
                },
                token_count=len(chunk_tokens),
                chunk_index=chunk_idx
            )
            chunks.append(chunk)
            
            # Move start index forward (with overlap)
            start_idx = end_idx - self.overlap_size
            chunk_idx += 1
            
            # Prevent infinite loop if overlap >= chunk_size
            if start_idx >= total_tokens:
                break
        
        # Update total_chunks in metadata
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)
        
        logger.info(
            "text_chunked",
            total_tokens=total_tokens,
            num_chunks=len(chunks),
            avg_chunk_size=total_tokens / len(chunks) if chunks else 0
        )
        
        return chunks
    
    def chunk_document(
        self,
        content: str,
        source: str,
        source_id: str,
        author: str = None,
        timestamp: str = None,
        url: str = None,
        additional_metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        Chunk a document with standard metadata.
        
        Args:
            content: Document content
            source: Source type (slack, notion, drive)
            source_id: Unique identifier from source
            author: Author/user who created content
            timestamp: Creation/modification timestamp
            url: Source URL if available
            additional_metadata: Any additional metadata
            
        Returns:
            List of chunks with metadata
        """
        base_metadata = {
            "source": source,
            "source_id": source_id,
            "author": author,
            "timestamp": timestamp,
            "url": url,
            **(additional_metadata or {})
        }
        
        return self.chunk_text(content, base_metadata)


if __name__ == "__main__":
    # Test the chunker
    chunker = ContentChunker(chunk_size=100, overlap_size=20)
    
    test_text = """
    This is a test document that will be chunked into smaller pieces.
    Each chunk will have approximately 100 tokens with 20 tokens of overlap
    between consecutive chunks. This ensures context is preserved across
    chunk boundaries and improves retrieval quality in vector search.
    """ * 5
    
    chunks = chunker.chunk_document(
        content=test_text,
        source="test",
        source_id="test-123",
        author="test_user",
        timestamp="2024-01-01T00:00:00Z"
    )
    
    print(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Content preview: {chunk.content[:100]}...")
        print(f"  Metadata: {chunk.metadata}")
