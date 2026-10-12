"""Keep all generated projects, SDK objects, assets and reports out of the tools checkout."""
from pathlib import Path

def private_output(path, inputs=()):
    path=Path(path).resolve();repository=Path(__file__).resolve().parents[2]
    if path==repository or repository in path.parents or path in repository.parents:
        raise ValueError('Output must be outside the public tools checkout')
    for item in inputs:
        item=Path(item).resolve()
        if path==item or item in path.parents or path in item.parents:
            raise ValueError('Output must not overlap a source input')
    return path
