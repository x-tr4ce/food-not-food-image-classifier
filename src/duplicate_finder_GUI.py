#!/usr/bin/env python3
"""
duplicate_finder_ui.py

Interactive GUI to review groups of similar images in-place.
Users can click on the image to keep, then delete the rest in that group, or skip the group entirely.
"""

import os
import io
from pathlib import Path
from PIL import Image, ImageTk
import imagehash
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
import tkinter as tk
import tkinter.messagebox

# ---------- Duplicate detection pipeline functions ----------

def find_image_files(src_dir: Path, extensions=None) -> list[Path]:
    if extensions is None:
        extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    return [p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in extensions]


def compute_hash(path: Path) -> tuple[Path, imagehash.ImageHash]:
    with Image.open(path) as img:
        return path, imagehash.phash(img)


def compute_hashes(paths: list[Path]) -> dict[Path, imagehash.ImageHash]:
    hashes = {}
    with ProcessPoolExecutor() as executor:
        for path, h in executor.map(compute_hash, paths):
            hashes[path] = h
    return hashes


def bucket_hashes(hashes: dict[Path, imagehash.ImageHash], prefix_bits: int) -> dict[int, list[tuple[Path, imagehash.ImageHash]]]:
    buckets = defaultdict(list)
    for path, h in hashes.items():
        h_int = int(str(h), 16)
        key = h_int >> (64 - prefix_bits)
        buckets[key].append((path, h))
    return buckets


def group_similar_in_bucket(bucket_items, threshold: int) -> list[list[Path]]:
    groups = []
    used = set()
    for i, (path, h) in enumerate(bucket_items):
        if path in used:
            continue
        group = [path]
        used.add(path)
        for other_path, other_h in bucket_items[i+1:]:
            if other_path not in used and (h - other_h) <= threshold:
                group.append(other_path)
                used.add(other_path)
        if len(group) > 1:
            groups.append(group)
    return groups


def group_similar_images(buckets, threshold: int) -> list[list[Path]]:
    groups = []
    for bucket_items in buckets.values():
        groups.extend(group_similar_in_bucket(bucket_items, threshold))
    return groups

# ---------- Thumbnail utility ----------


def make_thumbnail(path, size=(500,500)):
    img = Image.open(path)
    img.thumbnail(size)
    return ImageTk.PhotoImage(img)

def review_group(group):
    win = tk.Toplevel()
    win.title(f"Review {group[0].parent.name}")
    sel = tk.IntVar(value=-1)

    # Thumbnails + radio buttons
    for idx, path in enumerate(group):
        thumb = make_thumbnail(path)
        lbl = tk.Label(win, image=thumb)
        lbl.image = thumb
        lbl.grid(row=0, column=idx, padx=5, pady=5)
        rb = tk.Radiobutton(win, variable=sel, value=idx, text=path.name)
        rb.grid(row=1, column=idx)

    def on_keep():
        keep_idx = sel.get()
        if keep_idx >= 0:
            for i,p in enumerate(group):
                if i != keep_idx:
                    p.unlink(missing_ok=True)
        win.destroy()

    def on_skip():
        win.destroy()

    def on_del_all():
        for p in group:
            p.unlink(missing_ok=True)
        win.destroy()

    btn_keep = tk.Button(win, text="Keep Selected", command=on_keep)
    btn_skip = tk.Button(win, text="Skip",         command=on_skip)
    btn_delete_all = tk.Button(win, text="Delete All", command=on_del_all)
    btn_keep.grid(row=2, column=0, pady=10)
    btn_skip.grid(row=2, column=1, pady=10)
    btn_delete_all.grid(row=2, column=2, pady=10)
    win.wait_window()

def review_all(groups):
    def on_keep():
        keep_idx = sel.get()
        if keep_idx >= 0:
            for i, p in enumerate(current_group):
                if i != keep_idx:
                    p.unlink(missing_ok=True)
        next_group()

    def on_skip():
        next_group()

    def on_close():
        nonlocal running
        running = False
        win.destroy()

    def on_del_all():
        if current_group is not None:
            for p in current_group:
                p.unlink(missing_ok=True)
        next_group()

    def show_group(group):
        # Clear previous widgets
        for widget in win.winfo_children():
            widget.destroy()

        # ── Progress indicator ────────────────────────────────────
        progress = f"Group {group_idx + 1} of {len(groups)}"
        tk.Label(win, text=progress).grid(row=0, column=0, columnspan=len(group), pady=(10, 0))

        # Thumbnails + radio buttons
        for idx, path in enumerate(group):
            thumb = make_thumbnail(path)
            lbl = tk.Label(win, image=thumb)
            lbl.image = thumb
            lbl.grid(row=1, column=idx, padx=5, pady=5)
            rb = tk.Radiobutton(win, variable=sel, value=idx, text=path.name)
            rb.grid(row=2, column=idx)
        btn_keep = tk.Button(win, text="Keep Selected", command=on_keep)
        btn_skip = tk.Button(win, text="Skip", command=on_skip)
        btn_delete_all = tk.Button(win, text="Delete All", command=on_del_all)
        btn_keep.grid(row=3, column=0, pady=10)
        btn_skip.grid(row=3, column=1, pady=10)
        btn_delete_all.grid(row=3, column=2, pady=10)
        win.title(f"Review {group[0].parent.name}")

    def next_group():
        nonlocal group_idx, current_group
        group_idx += 1
        if group_idx < len(groups) and running:
            current_group = groups[group_idx]
            sel.set(-1)
            show_group(current_group)
        else:
            win.destroy()

    root = tk.Tk()
    root.withdraw()
    win = tk.Toplevel()
    win.protocol("WM_DELETE_WINDOW", on_close)
    sel = tk.IntVar(value=-1)
    group_idx = -1
    running = True
    current_group = None
    next_group()
    win.wait_window()
    if running:
        tkinter.messagebox.showinfo("Done", "All groups reviewed.")
    root.destroy()

if __name__ == "__main__":
    # Replace this with your grouping logic that produces `groups: list[list[Path]]`
    from duplicate_finder import find_image_files, compute_hashes, bucket_hashes, group_similar_images
    SRC = Path(__file__).parent.parent / "data" / "raw" / "restaurant_images"
    files  = find_image_files(SRC)

    if not files:
        raise FileNotFoundError(f"No image files found in {SRC}. Please check the directory structure.")

    hashes = compute_hashes(files)
    buckets= bucket_hashes(hashes, prefix_bits=12)
    groups = group_similar_images(buckets, threshold=5)

    if not groups:
        print("No similar image groups found.")
    else:
        review_all(groups)