#!/usr/bin/env python3
import cv2
import shutil
from pathlib import Path

def is_blurry(image_path: Path, threshold: float = 100.0) -> bool:
    """
    Check if an image is blurry using the Laplacian variance method.
    Laplacian variance explanation: A low variance indicates a blurry image, as the edges are not well defined.
    Args:
        image_path (Path): Path to the image file.
        threshold (float): Variance threshold below which the image is considered blurry.

    Returns:
        bool: True if the image is blurry, False otherwise.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False  # skip unreadable files
    fm = cv2.Laplacian(img, cv2.CV_64F).var()
    return fm < threshold

def collect_blurry(src_dir: Path, review_dir: Path, threshold: float = 100.0):
    """
    Collects blurry images from the source directory and copies them to the review directory.

    Args:
        src_dir (Path): Source directory containing images to check.
        review_dir (Path): Directory where flagged blurry images will be copied.
        threshold: float: Variance threshold for blurriness detection. Higher values mean stricter detection (more images flagged).

    Returns:

    """
    review_dir.mkdir(parents=True, exist_ok=True)

    exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    for img_path in src_dir.rglob("*"):
        if img_path.suffix.lower() not in exts:
            continue
        # Skip files already in the review_dir
        if review_dir in img_path.parents:
            continue
        if is_blurry(img_path, threshold):
            img_path.rename(review_dir / img_path.name)
            print(f"-> Flagged blurry: {img_path.name}")

if __name__ == "__main__":
    SRC        = Path(__file__).parent.parent / "data" / "raw" / "restaurant_images" / "non_food"
    REVIEW_DIR = SRC / "blurry_review"
    THRESHOLD  = 5.0   # tweak: higher → stricter (more images flagged)

    print(f"Scanning {SRC} for blur (threshold={THRESHOLD})…")
    collect_blurry(SRC, REVIEW_DIR, THRESHOLD)
    print(f"Done. Blurry images copied to: {REVIEW_DIR}")
