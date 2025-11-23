"""
Embedding generation module using OpenAI API.
"""
import os
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
import structlog
import tiktoken
from dataclasses import dataclass
from datetime import datetime

logger = structlog.get_logger()


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    vector: List[float]
    model: str
    token_count: int
    cost_usd: float


class Embedder:
    """Generates embeddings using OpenAI API with cost tracking."""
    
    # Cost per 1M tokens for different models
    COSTS = {
        "text-embedding-3-small": 0.02,  # $0.02 per 1M tokens
        "text-embedding-3-large": 0.13,  # $0.13 per 1M tokens
        "text-embedding-ada-002": 0.10,  # $0.10 per 1M tokens (legacy)
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        monthly_budget_usd: float = 100.0
    ):
        """
        Initialize embedder.
        
        Args:
            api_key: OpenAI API key (reads from OPENAI_API_KEY env var if not provided)
            model: Embedding model to use
            batch_size: Number of texts to embed per API call
            monthly_budget_usd: Monthly budget cap in USD
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.batch_size = batch_size
        self.monthly_budget_usd = monthly_budget_usd
        
        # Cost tracking
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
    def estimate_cost(self, text: str) -> float:
        """
        Estimate cost for embedding a text.
        
        Args:
            text: Text to estimate cost for
            
        Returns:
            Estimated cost in USD
        """
        tokens = len(self.encoding.encode(text))
        cost_per_token = self.COSTS.get(self.model, 0.02) / 1_000_000
        return tokens * cost_per_token
    
    def check_budget(self, estimated_cost: float) -> bool:
        """
        Check if operation is within budget.
        
        Args:
            estimated_cost: Estimated cost of operation
            
        Returns:
            True if within budget, False otherwise
        """
        projected_cost = self.total_cost_usd + estimated_cost
        
        if projected_cost > self.monthly_budget_usd:
            logger.warning(
                "budget_exceeded",
                current_cost=self.total_cost_usd,
                projected_cost=projected_cost,
                budget=self.monthly_budget_usd
            )
            return False
        
        # Alert at 75% threshold
        if projected_cost / self.monthly_budget_usd >= 0.75:
            logger.warning(
                "budget_alert",
                usage_percent=round(projected_cost / self.monthly_budget_usd * 100, 2),
                current_cost=projected_cost,
                budget=self.monthly_budget_usd
            )
        
        return True
    
    def embed_text(self, text: str) -> Optional[EmbeddingResult]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult or None if budget exceeded
        """
        if not text or not text.strip():
            logger.warning("empty_text_for_embedding")
            return None
        
        # Pre-flight cost check
        estimated_cost = self.estimate_cost(text)
        if not self.check_budget(estimated_cost):
            logger.error("embedding_halted_budget_exceeded")
            return None
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens
            actual_cost = (tokens_used / 1_000_000) * self.COSTS.get(self.model, 0.02)
            
            # Track costs
            self.total_tokens_used += tokens_used
            self.total_cost_usd += actual_cost
            
            logger.info(
                "embedding_generated",
                tokens=tokens_used,
                cost_usd=round(actual_cost, 6),
                total_cost_usd=round(self.total_cost_usd, 4)
            )
            
            return EmbeddingResult(
                vector=embedding,
                model=self.model,
                token_count=tokens_used,
                cost_usd=actual_cost
            )
            
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return None
    
    def embed_batch(
        self,
        texts: List[str],
        metadata: List[Dict[str, Any]] = None
    ) -> List[Optional[EmbeddingResult]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            metadata: Optional metadata for each text
            
        Returns:
            List of EmbeddingResults
        """
        if not texts:
            return []
        
        # Estimate total cost
        total_estimated_cost = sum(self.estimate_cost(text) for text in texts if text)
        
        if not self.check_budget(total_estimated_cost):
            logger.error("batch_embedding_halted_budget_exceeded")
            return [None] * len(texts)
        
        results = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                tokens_used = response.usage.total_tokens
                actual_cost = (tokens_used / 1_000_000) * self.COSTS.get(self.model, 0.02)
                
                # Track costs
                self.total_tokens_used += tokens_used
                self.total_cost_usd += actual_cost
                
                logger.info(
                    "batch_embeddings_generated",
                    batch_size=len(batch),
                    tokens=tokens_used,
                    cost_usd=round(actual_cost, 6),
                    total_cost_usd=round(self.total_cost_usd, 4)
                )
                
                # Create results for each embedding
                for j, embedding_data in enumerate(response.data):
                    results.append(EmbeddingResult(
                        vector=embedding_data.embedding,
                        model=self.model,
                        token_count=tokens_used // len(batch),  # Approximate
                        cost_usd=actual_cost / len(batch)  # Approximate
                    ))
                    
            except Exception as e:
                logger.error("batch_embedding_failed", error=str(e), batch_start=i)
                # Add None for failed batch
                results.extend([None] * len(batch))
        
        return results
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost tracking summary.
        
        Returns:
            Dictionary with cost metrics
        """
        return {
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "monthly_budget_usd": self.monthly_budget_usd,
            "budget_used_percent": round(
                (self.total_cost_usd / self.monthly_budget_usd) * 100, 2
            ) if self.monthly_budget_usd > 0 else 0,
            "model": self.model
        }


if __name__ == "__main__":
    # Test the embedder
    from dotenv import load_dotenv
    load_dotenv()
    
    embedder = Embedder(monthly_budget_usd=1.0)  # Small budget for testing
    
    test_texts = [
        "Knowledge summarizer agent processes documents from multiple sources.",
        "Embeddings are generated using OpenAI's text-embedding-3-small model.",
        "Cost tracking ensures we stay within budget limits."
    ]
    
    print("Embedding batch of texts...")
    results = embedder.embed_batch(test_texts)
    
    for i, result in enumerate(results):
        if result:
            print(f"\nText {i+1}:")
            print(f"  Vector dimensions: {len(result.vector)}")
            print(f"  Tokens: {result.token_count}")
            print(f"  Cost: ${result.cost_usd:.6f}")
    
    print("\nCost Summary:")
    summary = embedder.get_cost_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
