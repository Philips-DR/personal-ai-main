"""Documentation generators — one function per output type.

All generators receive the repo analysis and key file contents,
and return a markdown string for their specific doc type.
"""

import json
import logging

from app.claude import invoke_claude

logger = logging.getLogger(__name__)


async def _generate(system_prompt: str, analysis: dict, file_contents: dict[str, str]) -> str:
    """Common generation function using Claude."""
    context = json.dumps({
        "analysis": analysis,
        "file_count": len(file_contents),
        "file_paths": list(file_contents.keys()),
    }, indent=2)

    return await invoke_claude(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": context}],
        max_tokens=4096,
        temperature=0.3,
    )


async def generate_readme(analysis: dict, file_contents: dict[str, str]) -> str:
    return await _generate(
        "Generate a comprehensive README.md for this repository. Include: project name, description, features, installation, usage, configuration, examples, and license. Use proper markdown formatting.",  # noqa: E501
        analysis, file_contents,
    )


async def generate_architecture(analysis: dict, file_contents: dict[str, str]) -> str:
    return await _generate(
        "Generate a system architecture document for this repository. Include: high-level overview, component diagram description, data flow, technology stack, and design decisions. Use markdown with clear sections.",  # noqa: E501
        analysis, file_contents,
    )


async def generate_module_docs(analysis: dict, file_contents: dict[str, str]) -> str:
    return await _generate(
        "Generate per-module documentation for this repository. For each key module/directory, document: purpose, inputs, outputs, key functions, and dependencies. Use markdown with headers per module.",  # noqa: E501
        analysis, file_contents,
    )


async def generate_workflow(analysis: dict, file_contents: dict[str, str]) -> str:
    return await _generate(
        "Generate workflow diagram descriptions for this repository in Mermaid-compatible format. Document: main user flows, data processing pipelines, API request/response flows. Include Mermaid diagram code blocks.",  # noqa: E501
        analysis, file_contents,
    )


async def generate_api_reference(analysis: dict, file_contents: dict[str, str]) -> str:
    return await _generate(
        "Generate an API reference document for this repository. List all API endpoints, their methods, parameters, request/response schemas, and authentication requirements. Use markdown tables. If no APIs exist, state that clearly.",  # noqa: E501
        analysis, file_contents,
    )


async def generate_setup_guide(analysis: dict, file_contents: dict[str, str]) -> str:
    return await _generate(
        "Generate a step-by-step setup guide for this repository. Include: prerequisites, environment setup, dependency installation, configuration, running locally, running tests, and deployment. Use numbered steps.",  # noqa: E501
        analysis, file_contents,
    )
