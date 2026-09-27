"""Shared setup for talking to Microsoft Foundry Local.

embeddings.py and llm.py both need a loaded model - this module owns that
setup so there's one FoundryLocalManager per process (the SDK enforces this
as a singleton).
"""

from foundry_local_sdk import Configuration, FoundryLocalManager


def get_manager() -> FoundryLocalManager:
    if FoundryLocalManager.instance is not None:
        return FoundryLocalManager.instance
    return FoundryLocalManager(Configuration(app_name="Beacon"))


def get_ready_model(alias: str):
    """Look up a model by alias, downloading and loading it if needed."""
    manager = get_manager()
    model = manager.catalog.get_model(alias)
    if model is None:
        raise RuntimeError(f"No Foundry Local model found for alias '{alias}'")
    model.download()
    model.load()
    return model
