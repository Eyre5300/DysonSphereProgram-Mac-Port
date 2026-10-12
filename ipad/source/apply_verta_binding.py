"""Restore Metal length metadata without changing original Verta storage/upload."""
import argparse
from pathlib import Path
from private_paths import private_output

def adapt(text):
    old = 'mat.SetBuffer("_VertaBuffer", cbuffer);'
    new = 'mat.PortSetBuffer("_VertaBuffer", cbuffer);'
    if text.count(new) == 1 and old not in text:
        return text
    if text.count(old) != 1 or new in text:
        raise ValueError("Unsupported Verta material binding; refusing a partial patch")
    return text.replace(old, new, 1)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, required=True)
    args = p.parse_args()
    target = private_output(args.project) / "Assets/Scripts/Assembly-CSharp/VertaBuffer.cs"
    target.write_text(adapt(target.read_text()))

if __name__ == "__main__":
    main()
