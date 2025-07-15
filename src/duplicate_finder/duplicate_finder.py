#!/usr/bin/env python3
"""
duplicate_finder.py

Detects visually similar images in a directory by computing perceptual hashes,
organizes potential duplicates into subfolders for manual review.
"""

import shutil
from pathlib import Path
from PIL import Image
import imagehash
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict


def find_image_files(src_dir: Path, extensions=None) -> list[Path]:
    """
    Recursively collect image file paths in the given directory matching allowed extensions.

    Args:
        src_dir (Path): Directory to scan for image files.
        extensions (set of str, optional): File extensions to include (with leading dot).
            Defaults to common image types (.png, .jpg, etc.).

    Returns:
        list[Path]: List of image file paths.
    """
    if extensions is None:
        extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    return [p for p in src_dir.rglob("*") if p.is_file() and p.suffix.lower() in extensions]


def compute_hash(path: Path) -> tuple[Path, imagehash.ImageHash]:
    """
    Compute a perceptual hash for the image at the given path using pHash.

    Args:
        path (Path): Path to the image file.

    Returns:
        tuple[Path, imagehash.ImageHash]: Original path and its perceptual hash.
    """
    with Image.open(path) as img:
        return path, imagehash.phash(img)


def compute_hashes(paths: list[Path], use_processes: bool = True) -> dict[Path, imagehash.ImageHash]:
    """
    Compute perceptual hashes for all images in the provided paths.

    Args:
        paths (list[Path]): List of image file paths.
        use_processes (bool): Whether to parallelize via processes.

    Returns:
        dict[Path, imagehash.ImageHash]: Mapping of file paths to their hashes.
    """
    hashes = {}
    # Use process pool for CPU-bound hashing
    with ProcessPoolExecutor() as executor:
        for path, h in executor.map(compute_hash, paths):
            hashes[path] = h
    return hashes


def bucket_hashes(hashes: dict[Path, imagehash.ImageHash], prefix_bits: int) -> dict[int, list[tuple[Path, imagehash.ImageHash]]]:
    """
    Group images by the top `prefix_bits` of their hash to reduce comparisons.

    Args:
        hashes (dict[Path, imagehash.ImageHash]): Mapping of paths to hashes.
        prefix_bits (int): Number of highest-order bits to use as bucket key.

    Returns:
        dict[int, list[tuple[Path, imagehash.ImageHash]]]: Buckets of similar-prefix hashes.
    """
    buckets = defaultdict(list)
    for path, h in hashes.items():
        # Convert hex-string hash to integer
        h_int = int(str(h), 16)
        key = h_int >> (64 - prefix_bits) # Use top `prefix_bits` of hash
        buckets[key].append((path, h))
    return buckets


def group_similar_in_bucket(bucket_items: list[tuple[Path, imagehash.ImageHash]], threshold: int) -> list[list[Path]]:

    """
    Group similar images within a single bucket based on Hamming distance.
    This function compares each image's hash against others in the same bucket

    Args:
        bucket_items (list[tuple[Path, imagehash.ImageHash]]): List of (path, hash) tuples in a bucket.
        threshold (int): Maximum Hamming distance to consider images similar.

    Returns:
        list[list[Path]]: List of groups, each containing paths of similar images.

    """
    groups = []
    used = set()
    for i, (path, h) in enumerate(bucket_items):
        if path in used:
            continue
        group = [path]
        used.add(path)
        for other_path, other_h in bucket_items[i+1:]:
            if other_path in used:
                continue
            if (h - other_h) <= threshold:
                group.append(other_path)
                used.add(other_path)
        if len(group) > 1:
            groups.append(group)
    return groups


def group_similar_images(buckets: dict[int, list[tuple[Path, imagehash.ImageHash]]], threshold: int) -> list[list[Path]]:
    """
    Group similar images across all buckets based on Hamming distance.

    Args:
        buckets (dict[int, list[tuple[Path, imagehash.ImageHash]]]): Buckets of images.
        threshold (int): Maximum Hamming distance to consider images similar.

    Returns:
        list[list[Path]]: List of groups, each containing the paths of similar images.

    """
    groups = []
    for bucket_items in buckets.values():
        groups.extend(group_similar_in_bucket(bucket_items, threshold))
    return groups


def copy_groups(groups: list[list[Path]], out_dir: Path) -> None:
    """
    Copy each group of similar images into its own subfolder under `out_dir`.

    Args:
        groups (list[list[Path]]): Groups of similar image paths.
        out_dir (Path): Base directory to create group_x folders.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, group in enumerate(groups, start=1):
        grp_dir = out_dir / f"group_{idx}"
        grp_dir.mkdir(exist_ok=True)
        for path in group:
            shutil.copy2(path, grp_dir)
        print(f"Group {idx}: {len(group)} images copied to {grp_dir}")


def main():
    """
    Main entry point: configure paths and parameters, then run the duplicate grouping pipeline.
    """
    # --- Configuration ---
    SRC = Path(__file__).parent.parent.parent / "data" / "raw"
    OUT = SRC / "duplicates"
    THRESHOLD = 25       # Max Hamming distance for similarity
    PREFIX_BITS = 12    # Bits to bucket hashes and reduce comparisons

    print(f"Scanning images in: {SRC}")
    image_paths = find_image_files(SRC)
    print(f"Found {len(image_paths)} images to process.")

    print("Computing perceptual hashes in parallel...")
    hashes = compute_hashes(image_paths)

    print("Bucketing hashes to limit comparisons...")
    buckets = bucket_hashes(hashes, PREFIX_BITS)

    print("Grouping similar images within each bucket...")
    groups = group_similar_images(buckets, THRESHOLD)
    print(f"Identified {len(groups)} groups of similar images.")

    print(f"Copying groups to: {OUT}")
    copy_groups(groups, OUT)

    print("All images have been processed successfully. Review your groups for manual review.")


if __name__ == "__main__":
    main()
