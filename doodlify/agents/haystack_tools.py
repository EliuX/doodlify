"""
Haystack tool wrappers for Doodlify agents.

These are thin wrappers that make the existing agents (AnalyzerAgent, ImageAgent, TextAgent)
available as Haystack tools for the agentic orchestrator. The actual logic lives in the agents.
"""

from typing import Dict, Any, List, Optional
from haystack.tools import tool
from pathlib import Path


@tool
def analyze_codebase_tool(
    repo_path: str,
    project_description: str,
    sources: Optional[List[str]] = None,
    selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wrapper for AnalyzerAgent.analyze_codebase.
    Analyzes a codebase to identify files for event-themed modifications.
    """
    from doodlify.agents.analyzer_agent import AnalyzerAgent
    import os
    
    agent = AnalyzerAgent(api_key=os.getenv('OPENAI_API_KEY'))
    return agent.analyze_codebase(
        repo_path=Path(repo_path),
        sources=sources or [],
        project_description=project_description,
        selector=selector
    )


@tool
def process_images_tool(
    repo_path: str,
    image_files: List[str],
    event_name: str,
    event_description: str,
    sources: Optional[List[str]] = None,
    palette: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Wrapper that processes multiple images using ImageAgent.
    Replicates the file search logic from assistant mode orchestrator.
    """
    from doodlify.agents.image_agent import ImageAgent
    import os
    import logging
    
    # Setup debug logging
    log_file = Path(repo_path).parent / "agentic_debug.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("process_images_tool")
    
    logger.info(f"=== PROCESS IMAGES TOOL CALLED ===")
    logger.info(f"repo_path: {repo_path}")
    logger.info(f"event_name: {event_name}")
    logger.info(f"image_files count: {len(image_files)}")
    logger.info(f"sources: {sources}")
    
    repo = Path(repo_path)
    logger.info(f"Repo path exists: {repo.exists()}")
    logger.info(f"Repo absolute path: {repo.absolute()}")
    
    image_agent = ImageAgent(api_key=os.getenv('OPENAI_API_KEY'))
    logger.info(f"ImageAgent initialized, has transform_image: {hasattr(image_agent, 'transform_image')}")
    
    def find_file_in_repo(rel_path: str) -> Optional[Path]:
        """Find a file in the repo, searching in source directories."""
        # Remove leading slash if present
        clean_path = rel_path.lstrip('/')
        
        # Try direct path from repo root
        candidate = repo / clean_path
        if candidate.exists() and not any(x in str(candidate) for x in ['.next', 'dist', 'out', 'node_modules']):
            return candidate
        
        # Try in each source directory
        for source in (sources or []):
            candidate = repo / source / clean_path
            if candidate.exists() and not any(x in str(candidate) for x in ['.next', 'dist', 'out', 'node_modules']):
                return candidate
        
        # If not found, search recursively (skip build dirs)
        filename = Path(clean_path).name
        for source_dir in ([repo] + [repo / s for s in (sources or [])]):
            if not source_dir.exists():
                continue
            for candidate in source_dir.rglob(filename):
                # Skip build/dist directories
                path_str = str(candidate)
                if any(x in path_str for x in ['node_modules', '.next', 'dist', 'out', '.git', 'coverage']):
                    continue
                # Prefer files in 'src' or 'public' directories
                if 'src' in path_str or 'public' in path_str:
                    return candidate
        
        return None
    
    results = []
    for img_path in image_files:
        logger.info(f"\n--- Processing image: {img_path} ---")
        try:
            full_path = find_file_in_repo(img_path)
            logger.info(f"Found file at: {full_path}")
            
            if not full_path:
                logger.warning(f"File not found: {img_path}")
                results.append({"file": img_path, "status": "skipped", "reason": "file not found"})
                continue
            
            logger.info(f"File exists: {full_path.exists()}")
            logger.info(f"File is supported: {image_agent.is_supported_format(full_path)}")
            
            # Delegate to ImageAgent (same as assistant mode)
            # IMPORTANT: Pass output_path so the file is actually saved!
            logger.info(f"Calling image_agent.transform_image() with output_path={full_path}...")
            image_bytes = image_agent.transform_image(
                image_path=full_path,
                event_name=event_name,
                event_description=event_description,
                output_path=full_path  # THIS IS CRITICAL - saves the transformed image
            )
            logger.info(f"Transform result: {len(image_bytes)} bytes")
            logger.info(f"File modified, checking size...")
            logger.info(f"File size after transform: {full_path.stat().st_size}")
            logger.info(f"Transform completed and saved for {img_path}")
            
            results.append({"file": img_path, "status": "success", "size_bytes": len(image_bytes)})
        except Exception as e:
            logger.error(f"Error processing {img_path}: {e}", exc_info=True)
            results.append({"file": img_path, "status": "error", "error": str(e)})
    
    success_count = sum(1 for r in results if r["status"] == "success")
    return {
        "total": len(image_files),
        "successful": success_count,
        "failed": len(image_files) - success_count,
        "results": results
    }
