"""Shared Bedrock client factory — uses bearer token auth only.

Loads AWS_BEARER_TOKEN_BEDROCK from settings and sets it in os.environ
so botocore's native bearer token provider handles authentication.
"""

import logging

import botocore.session

from app.config import settings

logger = logging.getLogger(__name__)

_bedrock_client = None


def get_bedrock_client():
    """Get a singleton Bedrock Runtime client using bearer token auth."""
    global _bedrock_client
    if _bedrock_client is not None:
        return _bedrock_client

    token = settings.aws_bearer_token_bedrock
    if not token:
        raise ValueError("AWS_BEARER_TOKEN_BEDROCK is not set in environment")

    token = token.strip().rstrip(",")
    region = settings.aws_region

    # Ensure botocore's native bearer token provider can find the token
    import os
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = token

    session = botocore.session.get_session()

    _bedrock_client = session.create_client(
        "bedrock-runtime",
        region_name=region,
    )

    logger.info("Bedrock client initialized (region=%s, auth=bearer_token)", region)
    return _bedrock_client
