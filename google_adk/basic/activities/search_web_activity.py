from temporalio import activity


@activity.defn
async def search_web(query: str) -> str:
    """Search the web for information (mock implementation)."""
    return f'Search results for "{query}": [Result 1: Overview] [Result 2: Details] [Result 3: Examples]'
