import asyncio
import sys
from argparse import ArgumentParser
from uuid import UUID
from .analysis_service import AnalysisService
from logging import getLogger
from ..container import get_container, initialize_container, shutdown_container

logger = getLogger(__name__)

def get_analysis_service() -> AnalysisService:
    """Get analysis service from container."""
    container = get_container()
    return container.get(AnalysisService)


def main():
    """CLI entry point."""
    parser = ArgumentParser(description="Run code analysis for a project")
    parser.add_argument("job_id", help="Analysis job ID (UUID)")
    args = parser.parse_args()
    
    # Initialize container
    initialize_container()

    service = get_analysis_service()

    try:
        job_id = UUID(args.job_id)
        # Run async analysis
        asyncio.run(service.run_analysis(job_id))
        sys.exit(0)
    except ValueError as e:
        logger.error(f"Invalid job ID: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1) 
    
    # Shutdown
    logger.info("Shutting down Legacy Code Analysis API")
    shutdown_container()
    logger.info("Shutdown complete")

if __name__ == '__main__':
    main()