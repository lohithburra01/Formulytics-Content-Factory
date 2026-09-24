"""Trace the Baku SVG road ribbon with the official 2025 position lap as a guide.

The supplied SVG is a filled, self-intersecting ribbon; the generic SVG
converter would drive both edges. Raster skeleton points provide its centre,
and the position trace supplies the unambiguous circuit order and S/F.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import networkx as nx
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from svg_to_outline import (commands_to_polyline, compute_left_normals,
                            parse_svg_path_d, signed_area)
SVG = ROOT / "Baku_Formula_One_circuit_map.svg"
POS = ROOT / "cache/baku_2025_q_position.csv"
OUT = ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline.json"
AUDIT = ROOT / "cache/baku_svg_centerline_audit.json"
LENGTH_M = 6003.0
RASTER_SCALE = 3
N_OUT = 2000

path = next(e for e in ET.parse(SVG).getroot().iter()
            if e.attrib.get("id") == "path839")
boundary = np.asarray(commands_to_polyline(parse_svg_path_d(path.attrib["d"])))
gps = pd.read_csv(POS)[["X", "Y"]].to_numpy(dtype=float)
gps[:, 1] *= -1  # F1 y-up coordinates into SVG's y-down coordinates
gps_center = gps.mean(axis=0)
u = gps - gps_center

# Rasterize the filled road and locate its medial pixels.
origin = boundary.min(axis=0) - 10.0
pixel_boundary = np.rint((boundary - origin) * RASTER_SCALE).astype(np.int32)
size = pixel_boundary.max(axis=0) + 10
mask = np.zeros((size[1], size[0]), np.uint8)
cv2.fillPoly(mask, [pixel_boundary], 1)
skel = skeletonize(mask > 0)
yy, xx = np.where(skel)
nodes = list(zip(yy.tolist(), xx.tolist()))
node_set = set(nodes)
medial = np.column_stack((xx, yy)) / RASTER_SCALE + origin
tree = cKDTree(medial)

# The two shapes are already similarly oriented. Fit the small map distortion
# by nearest-medial-point residuals, with a weak penalty against shear.
bbox_scale = (boundary.max(axis=0) - boundary.min(axis=0)) / (
    gps.max(axis=0) - gps.min(axis=0))
initial = np.array([bbox_scale[0], 0, 0, bbox_scale[1],
                    *boundary.mean(axis=0)], dtype=float)


def transform(z):
    return u @ np.array([[z[0], z[2]], [z[1], z[3]]]) + z[4:]


def residual(z):
    dist = tree.query(transform(z))[0]
    return np.r_[np.minimum(dist, 10.0), (z[:4] - initial[:4]) * 300.0]


fit = least_squares(residual, initial, max_nfev=160)
registered = transform(fit.x)
fit_dist, indices = tree.query(registered)
if np.percentile(fit_dist, 95) > 2.5:
    raise RuntimeError("Position trace failed to register to Baku SVG ribbon")

# Follow each pair of position anchors along the medial graph. This preserves
# the SVG's corner detail while the anchors choose the correct branch at the
# close approaches and keep the official anti-clockwise driving direction.
graph = nx.Graph()
graph.add_nodes_from(nodes)
for y, x in nodes:
    for dy, dx in ((0, 1), (1, -1), (1, 0), (1, 1)):
        nxt = (y + dy, x + dx)
        if nxt in node_set:
            graph.add_edge((y, x), nxt, weight=np.hypot(dy, dx))
anchors = [nodes[i] for i in indices]
route = []
piece_lengths = []
for a, b in zip(anchors, anchors[1:] + anchors[:1]):
    path_nodes = nx.shortest_path(graph, a, b, weight="weight")
    route.extend(path_nodes[:-1])
    piece_lengths.append(nx.path_weight(graph, path_nodes, "weight") / RASTER_SCALE)
if max(piece_lengths) > 25.0:
    raise RuntimeError("SVG medial route jumped a circuit branch")
route = np.asarray(route, dtype=int)
raw_svg = route[:, ::-1] / RASTER_SCALE + origin
raw_math = raw_svg * [1, -1]
seg = np.linalg.norm(np.diff(np.vstack((raw_math, raw_math[0])), axis=0), axis=1)
arc = np.r_[0.0, np.cumsum(seg)]
scale_m = LENGTH_M / arc[-1]
raw_math *= scale_m
arc *= scale_m
grid = np.arange(N_OUT) * LENGTH_M / N_OUT
center = np.column_stack([np.interp(grid, arc, np.r_[raw_math[:, axis], raw_math[0, axis]])
                          for axis in (0, 1)])
center = gaussian_filter1d(center, sigma=1.4, axis=0, mode="wrap")
center_offset = center.mean(axis=0)
center -= center_offset
closed_length = np.linalg.norm(np.diff(np.vstack((center, center[0])), axis=0), axis=1).sum()
center *= LENGTH_M / closed_length
# Near the Old City, raster skeletonization joins two roads a few metres
# apart. At those two passes, use the registered position route to keep them
# distinct. Its matching is constrained to the same part of the lap.
gps_math = (registered * [1, -1] * scale_m - center_offset) * (LENGTH_M / closed_length)
gps_seg = np.linalg.norm(np.diff(np.vstack((gps_math, gps_math[0])), axis=0), axis=1)
gps_arc = np.r_[0.0, np.cumsum(gps_seg)]
gps_grid = np.linspace(0.0, gps_arc[-1], 4000, endpoint=False)
gps_dense = np.column_stack([
    np.interp(gps_grid, gps_arc, np.r_[gps_math[:, axis], gps_math[0, axis]])
    for axis in (0, 1)])
for crossing_station in (782, 1618):
    for station in range(crossing_station - 65, crossing_station + 66):
        index = station % N_OUT
        approx = int(index / N_OUT * len(gps_dense))
        candidates = np.arange(approx - 120, approx + 121) % len(gps_dense)
        nearest = candidates[np.argmin(np.linalg.norm(
            gps_dense[candidates] - center[index], axis=1))]
        weight = np.exp(-0.5 * ((station - crossing_station) / 20.0) ** 2)
        center[index] = (1.0 - weight) * center[index] + weight * gps_dense[nearest]
center = gaussian_filter1d(center, sigma=1.0, axis=0, mode="wrap")
if not LineString(np.vstack((center, center[0]))).is_simple:
    raise RuntimeError("Baku centreline crosses itself after the Old City repair")
center *= LENGTH_M / np.linalg.norm(
    np.diff(np.vstack((center, center[0])), axis=0), axis=1).sum()
if signed_area(center) <= 0:
    raise RuntimeError("Baku route has the wrong driving direction")

# The SVG width varies by section. Smooth its raster thickness and keep it
# within the circuit's published 7.6-13 m road width range.
distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
raw_width = 2.0 * distance[route[:, 0], route[:, 1]] / RASTER_SCALE * scale_m
raw_width = median_filter(raw_width, size=51, mode="wrap")
width = np.clip(np.interp(grid, arc, np.r_[raw_width, raw_width[0]]), 7.6, 13.0)
width = gaussian_filter1d(width, sigma=5, mode="wrap")
normal = compute_left_normals(center)
inner = center + normal * width[:, None] / 2.0
outer = center - normal * width[:, None] / 2.0
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"outer": outer.tolist(), "inner": inner.tolist()}), encoding="utf-8")

audit = dict(svg=str(SVG), position_source=str(POS),
             route="SVG filled-ribbon medial axis guided by 2025 Q position order",
             raster_scale=RASTER_SCALE, position_registration_svg_units=dict(
                 median=float(np.median(fit_dist)), p95=float(np.percentile(fit_dist, 95)),
                 maximum=float(fit_dist.max())),
             longest_anchor_segment_svg_units=float(max(piece_lengths)),
             raw_route_svg_units=float(arc[-1] / scale_m),
             scaled_length_m=float(np.linalg.norm(
                 np.diff(np.vstack((center, center[0])), axis=0), axis=1).sum()),
             width_m=dict(min=float(width.min()), median=float(np.median(width)),
                          max=float(width.max())),
             direction="anti-clockwise", stations=N_OUT)
AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
print(json.dumps(audit, indent=2))
print(f"wrote {OUT}")
