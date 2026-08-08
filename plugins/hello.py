"""Example plugin — hello world."""


def run(name: str = "world") -> dict:
    return {"message": f"Hello, {name}! This is the example plugin."}
