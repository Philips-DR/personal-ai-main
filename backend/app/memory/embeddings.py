import json
import logging

from app.bedrock import get_bedrock_client
from app.config import settings

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using Amazon Titan via Bedrock."""
    client = get_bedrock_client()
    body = json.dumps({"inputText": text})
    try:
        response = client.invoke_model(
            modelId=settings.titan_embedding_model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["embedding"]
    except Exception as e:
        logger.error("Failed to generate embedding: %s", e)
        raise


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    import asyncio

    tasks = [generate_embedding(t) for t in texts]
    return await asyncio.gather(*tasks)
