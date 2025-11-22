"""
Token volume estimator for cost projection.
"""
import json
from typing import Dict, List
from pathlib import Path
import tiktoken
import structlog

logger = structlog.get_logger()


class VolumeEstimator:
    """Estimates token volumes and costs for knowledge processing."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize volume estimator.

        Args:
            encoding_name: Tiktoken encoding to use (cl100k_base for GPT-4, GPT-3.5).
        """
        self.encoding = tiktoken.get_encoding(encoding_name)

        # Pricing per 1M tokens (as of 2024)
        self.pricing = {
            "embedding_ada": 0.10,  # $0.10 per 1M tokens
            "gpt4_input": 10.00,    # $10 per 1M input tokens
            "gpt4_output": 30.00,   # $30 per 1M output tokens
            "claude_input": 3.00,   # $3 per 1M input tokens (Sonnet)
            "claude_output": 15.00  # $15 per 1M output tokens (Sonnet)
        }

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to tokenize.

        Returns:
            Number of tokens.
        """
        return len(self.encoding.encode(text))

    def estimate_from_samples(
        self,
        sample_files: List[str],
        messages_per_week: int = 1000
    ) -> Dict:
        """
        Estimate weekly volume from sample data.

        Args:
            sample_files: List of sample JSON files to analyze.
            messages_per_week: Estimated new messages per week.

        Returns:
            Dictionary with volume estimates.
        """
        total_tokens = 0
        item_count = 0

        for file_path in sample_files:
            if not Path(file_path).exists():
                logger.warning("sample_file_not_found", file_path=file_path)
                continue

            with open(file_path, 'r') as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    text = self._extract_text(item)
                    tokens = self.count_tokens(text)
                    total_tokens += tokens
                    item_count += 1

        avg_tokens_per_item = total_tokens / item_count if item_count > 0 else 0

        # Weekly estimates
        weekly_tokens = avg_tokens_per_item * messages_per_week

        # Monthly estimates (4.33 weeks average)
        monthly_tokens = weekly_tokens * 4.33

        estimates = {
            "sample_stats": {
                "total_items": item_count,
                "total_tokens": total_tokens,
                "avg_tokens_per_item": round(avg_tokens_per_item, 2)
            },
            "weekly_estimate": {
                "new_items": messages_per_week,
                "tokens": round(weekly_tokens, 2)
            },
            "monthly_estimate": {
                "new_items": round(messages_per_week * 4.33, 2),
                "tokens": round(monthly_tokens, 2)
            },
            "cost_projections": self._calculate_costs(monthly_tokens)
        }

        logger.info(
            "volume_estimated",
            avg_tokens=avg_tokens_per_item,
            monthly_tokens=monthly_tokens
        )

        return estimates

    def _extract_text(self, item: Dict) -> str:
        """
        Extract text content from item.

        Args:
            item: Data item dictionary.

        Returns:
            Extracted text.
        """
        # Try common text fields
        text_fields = [
            "text", "content", "text_content", "body",
            "message", "description", "summary"
        ]

        text_parts = []
        for field in text_fields:
            if field in item and isinstance(item[field], str):
                text_parts.append(item[field])

        # Also include title if present
        if "title" in item:
            text_parts.append(item["title"])

        return " ".join(text_parts)

    def _calculate_costs(self, monthly_tokens: float) -> Dict:
        """
        Calculate monthly costs for different operations.

        Args:
            monthly_tokens: Estimated monthly token volume.

        Returns:
            Cost breakdown dictionary.
        """
        # Convert to millions of tokens
        tokens_millions = monthly_tokens / 1_000_000

        costs = {
            "embedding_generation": {
                "cost_usd": round(tokens_millions * self.pricing["embedding_ada"], 2),
                "description": "OpenAI embeddings (ada-002)"
            },
            "summarization_claude": {
                "input_cost_usd": round(tokens_millions * self.pricing["claude_input"], 2),
                "output_cost_usd": round((tokens_millions * 0.2) * self.pricing["claude_output"], 2),  # Assume 20% output
                "total_cost_usd": round(
                    (tokens_millions * self.pricing["claude_input"]) +
                    ((tokens_millions * 0.2) * self.pricing["claude_output"]),
                    2
                ),
                "description": "Claude Sonnet for summarization"
            },
            "total_estimated_monthly": 0
        }

        # Calculate total
        costs["total_estimated_monthly"] = round(
            costs["embedding_generation"]["cost_usd"] +
            costs["summarization_claude"]["total_cost_usd"],
            2
        )

        return costs

    def check_budget_compliance(
        self,
        estimated_monthly_cost: float,
        monthly_budget: float = 50.0
    ) -> Dict:
        """
        Check if estimated costs are within budget.

        Args:
            estimated_monthly_cost: Estimated monthly cost.
            monthly_budget: Monthly budget limit.

        Returns:
            Budget compliance report.
        """
        within_budget = estimated_monthly_cost <= monthly_budget
        utilization_percent = (estimated_monthly_cost / monthly_budget) * 100

        compliance = {
            "estimated_cost_usd": estimated_monthly_cost,
            "budget_limit_usd": monthly_budget,
            "utilization_percent": round(utilization_percent, 2),
            "within_budget": within_budget,
            "remaining_budget_usd": round(monthly_budget - estimated_monthly_cost, 2),
            "status": "✅ WITHIN BUDGET" if within_budget else "❌ OVER BUDGET"
        }

        logger.info(
            "budget_check_complete",
            cost=estimated_monthly_cost,
            budget=monthly_budget,
            within_budget=within_budget
        )

        return compliance

    def generate_report(self, output_file: str = "volume_estimate_report.json"):
        """
        Generate volume estimation report from sample files.

        Args:
            output_file: Output file path.
        """
        sample_files = [
            "sample_slack_messages.json",
            "sample_notion_pages.json",
            "sample_drive_docs.json"
        ]

        estimates = self.estimate_from_samples(sample_files)
        budget_check = self.check_budget_compliance(
            estimates["cost_projections"]["total_estimated_monthly"]
        )

        report = {
            "estimates": estimates,
            "budget_compliance": budget_check,
            "recommendations": self._generate_recommendations(estimates, budget_check)
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info("volume_report_generated", output_file=output_file)

        return report


    def _generate_recommendations(
        self,
        estimates: Dict,
        budget_check: Dict
    ) -> List[str]:
        """Generate recommendations based on estimates."""
        recommendations = []

        if not budget_check["within_budget"]:
            recommendations.append(
                "⚠️ Estimated costs exceed budget. Consider implementing rate limiting or batch processing."
            )

        monthly_tokens = estimates["monthly_estimate"]["tokens"]
        if monthly_tokens > 10_000_000:  # 10M tokens
            recommendations.append(
                "💡 High token volume detected. Consider caching frequently accessed content."
            )

        recommendations.append(
            "✅ Implement incremental updates to reduce redundant embedding generation."
        )
        recommendations.append(
            "💰 Monitor actual usage and adjust batch sizes to optimize costs."
        )

        return recommendations


if __name__ == "__main__":
    # Generate volume estimation report
    estimator = VolumeEstimator()
    report = estimator.generate_report()

    print("\n📊 Volume Estimation Report")
    print("=" * 60)
    print(f"\nSample Stats:")
    print(f"  Total items: {report['estimates']['sample_stats']['total_items']}")
    print(f"  Average tokens/item: {report['estimates']['sample_stats']['avg_tokens_per_item']}")

    print(f"\nMonthly Estimate:")
    print(f"  New items: {report['estimates']['monthly_estimate']['new_items']}")
    print(f"  Tokens: {report['estimates']['monthly_estimate']['tokens']:,.0f}")

    print(f"\nCost Projections:")
    costs = report['estimates']['cost_projections']
    print(f"  Embeddings: ${costs['embedding_generation']['cost_usd']}")
    print(f"  Summarization: ${costs['summarization_claude']['total_cost_usd']}")
    print(f"  Total: ${costs['total_estimated_monthly']}")

    print(f"\nBudget Compliance:")
    budget = report['budget_compliance']
    print(f"  {budget['status']}")
    print(f"  Utilization: {budget['utilization_percent']}%")
    print(f"  Remaining: ${budget['remaining_budget_usd']}")

    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  {rec}")
