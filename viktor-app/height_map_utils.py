import numpy as np


def crop_map(height_map, size=500):
    [w, h] = height_map.shape

    sx = int(w / 2 - size / 2)
    sy = int(h / 2 - size / 2)

    return height_map[sx : sx + size, sy : sy + size]


def merge_maps(terrain, surroundings, alternative):
    out = terrain["map"].copy()
    x, y = terrain["x"], terrain["y"]

    sx = surroundings["x"] - x
    sy = surroundings["y"] - y
    [w, h] = surroundings["map"].shape
    out[sx : sx + w, sy : sy + h] += surroundings["map"]

    sx = alternative["x"] - x
    sy = alternative["y"] - y
    [w, h] = alternative["map"].shape
    out[sx : sx + w, sy : sy + h] += alternative["map"]

    return out
