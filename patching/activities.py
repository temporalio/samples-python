from temporalio import activity


@activity.defn
async def pre_patch_activity() -> str:
    return "pre-patch"


@activity.defn
async def post_patch_activity() -> str:
    return "post-patch"
