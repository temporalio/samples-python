"""Activity from Node - Activity Definitions.

Activities that are called from a run_in_workflow node.
"""

from temporalio import activity


@activity.defn
async def validate_data(data: str) -> bool:
    """Validate the input data.

    In a real application, this could:
    - Check data format and schema
    - Verify required fields
    - Call external validation services
    """
    activity.logger.info(f"Validating data: {data}")

    # Simple validation - check if data is non-empty
    is_valid = bool(data and data.strip())

    activity.logger.info(f"Validation result: {is_valid}")
    return is_valid


@activity.defn
async def enrich_data(data: str) -> str:
    """Enrich the input data with additional information.

    In a real application, this could:
    - Call external APIs for data enrichment
    - Lookup data from databases
    - Apply transformations
    """
    activity.logger.info(f"Enriching data: {data}")

    # Simple enrichment - add metadata
    enriched = f"{data} [enriched at activity]"

    activity.logger.info(f"Enriched data: {enriched}")
    return enriched
