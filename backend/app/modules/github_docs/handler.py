import logging

from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse
from app.modules.base import ModuleHandler
from app.modules.github_docs.analyzer import analyze_repo
from app.modules.github_docs.exporter import bundle_markdown
from app.modules.github_docs.generators import (
    generate_api_reference,
    generate_architecture,
    generate_module_docs,
    generate_readme,
    generate_setup_guide,
    generate_workflow,
)
from app.modules.github_docs.repo_fetcher import (
    fetch_file_contents,
    fetch_repo_tree,
    select_key_files,
)

logger = logging.getLogger(__name__)


class GitHubDocsModule(ModuleHandler):
    @property
    def name(self) -> str:
        return "github_docs"

    @property
    def supported_intents(self) -> list[Intent]:
        return [Intent.GITHUB_DOCUMENT]

    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        repo_url = request.parameters.get("repo_url")
        private_token = request.parameters.get("private_token")

        if not repo_url:
            return ModuleResponse(content="Please provide a GitHub repository URL.")

        try:
            # Step 1: Fetch repo tree
            tree_data = await fetch_repo_tree(repo_url, token=private_token)
            files = tree_data["files"]

            # Step 2: Select and fetch key files
            key_paths = select_key_files(files)
            file_contents = await fetch_file_contents(repo_url, key_paths, token=private_token)

            # Step 3: Analyze repo
            analysis = await analyze_repo(files, file_contents)

            # Step 4: Generate all 6 doc types
            docs = {}
            generators = {
                "readme": generate_readme,
                "architecture": generate_architecture,
                "module_docs": generate_module_docs,
                "workflow": generate_workflow,
                "api_reference": generate_api_reference,
                "setup_guide": generate_setup_guide,
            }

            for doc_type, generator in generators.items():
                try:
                    docs[doc_type] = await generator(analysis, file_contents)
                    logger.info("Generated %s doc", doc_type)
                except Exception as e:
                    logger.error("Failed to generate %s: %s", doc_type, e)
                    docs[doc_type] = f"Generation failed: {e}"

            # Step 5: Bundle
            repo_name = f"{tree_data['owner']}/{tree_data['repo']}"
            full_bundle = bundle_markdown(docs, repo_name)

            # Build summary response
            generated = [k for k, v in docs.items() if not v.startswith("Generation failed")]
            lines = [
                f"**Documentation generated for {repo_name}** ({len(generated)}/6 types)\n",
                "Generated docs:",
            ]
            for doc_type in generated:
                lines.append(f"  - {doc_type}")

            lines.append(f"\nTotal documentation: {len(full_bundle)} characters")

            return ModuleResponse(
                content="\n".join(lines),
                structured={
                    "repo": repo_name,
                    "docs": docs,
                    "analysis": analysis,
                },
                memory_updates=[{
                    "category": "fact",
                    "subject": f"GitHub docs: {repo_name}",
                    "content": f"Generated {len(generated)} documentation types for {repo_name}.",
                }],
            )

        except Exception as e:
            logger.error("GitHub docs generation failed: %s", e)
            return ModuleResponse(content=f"Failed to generate documentation: {e}")
