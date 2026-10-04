"""Selvstændig tegnemotor. Ingen afhængighed af Streamlit eller andre projektmoduler."""

from __future__ import annotations

import io
import math
import re
import threading
from dataclasses import dataclass
from html.parser import HTMLParser

import matplotlib
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, Polygon
from PIL import Image


MAX_PIXELS = 24_000_000
MAX_SIDE = 8000
RENDER_LOCK = threading.RLock()
DEFAULTS = {
    "schema_version": 1, "generator": "flow", "chapter": 0,
    "theme": "Havstrømme", "theme_text": "", "preset": "Tidevand",
    "palette": "Hav og guld", "colors": ["#193e52", "#387782", "#86a7a0", "#d5ac67", "#b96645"],
    "background": "#f5f1e7", "width": 1600, "height": 900, "dpi": 300,
    "seed": 42, "density": 55, "complexity": 6, "symmetry": 6,
    "variation": 0.35, "stroke": 1.0, "margin": 0.09,
    "mode": "standard", "transparent": False, "book_style": False,
}


def validate_config(settings: dict) -> dict:
    """Kontrollér også indlæste JSON-filer, før der tegnes noget."""
    if not isinstance(settings, dict):
        raise ValueError("Indstillingerne skal være et JSON-objekt.")
    config = dict(DEFAULTS)
    config.update({key: value for key, value in settings.items() if key in DEFAULTS})
    limits = {"width": (64, MAX_SIDE), "height": (64, MAX_SIDE), "dpi": (72, 600),
              "seed": (0, 2**32 - 1), "density": (5, 100), "complexity": (2, 10),
              "symmetry": (2, 16), "chapter": (0, 15), "schema_version": (1, 1)}
    for key, (low, high) in limits.items():
        value = config[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{key} skal være et heltal mellem {low} og {high}.")
    for key, (low, high) in {"variation": (0, 1), "stroke": (0.3, 3), "margin": (0.02, 0.25)}.items():
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} skal ligge mellem {low} og {high}.")
    if config["width"] * config["height"] > MAX_PIXELS:
        raise ValueError("Vælg højst 24 millioner pixels i alt, fx 6000 × 4000.")
    if not isinstance(config["generator"], str) or config["generator"] not in RENDERERS:
        raise ValueError("Ukendt kunstgenerator.")
    for key in ("theme", "theme_text", "palette", "preset", "mode"):
        if not isinstance(config[key], str) or len(config[key]) > 2000:
            raise ValueError(f"{key} skal være en tekst på højst 2000 tegn.")
    for key in ("transparent", "book_style"):
        if type(config[key]) is not bool:
            raise ValueError(f"{key} skal være true eller false.")
    colors = config["colors"]
    if not isinstance(colors, list) or not 2 <= len(colors) <= 12:
        raise ValueError("Paletten skal indeholde 2–12 farver.")
    for color in colors + [config["background"]]:
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Farver skal skrives som sekscifrede hex-koder, fx #193e52.")
    return config


def _bounds(config):
    aspect = config["width"] / config["height"]
    return aspect * (1 - config["margin"] * 2), 1 - config["margin"] * 2


def _lines(ax, segments, colors, widths, alpha=1):
    collection = LineCollection(segments, colors=colors, linewidths=widths, alpha=alpha,
                                capstyle="round", joinstyle="round")
    ax.add_collection(collection)


def geometry(ax, config, rng, unit):
    """Gentagelser og betingelser fordeler buer og geometriske figurer."""
    bx, by = _bounds(config)
    rows = 3 + config["density"] // 13
    cols = max(2, round(rows * bx / by))
    cell = min(2 * bx / cols, 2 * by / rows)
    colors = config["colors"]
    for row in range(rows):
        for col in range(cols):
            x = (col - (cols - 1) / 2) * cell
            y = (row - (rows - 1) / 2) * cell
            radius = cell * (0.32 + rng.random() * config["variation"] * 0.12)
            color = colors[(row + col) % len(colors)]
            kind = (row + col) % 3
            if config["mode"] == "rings":
                for ring in range(max(2, config["complexity"] // 2)):
                    ax.add_patch(Circle((x, y), radius * (1 - ring / (config["complexity"] / 2 + 1)),
                                        fill=False, edgecolor=color, lw=2.4 * unit, alpha=0.9))
                continue
            if kind == 0:
                for index in range(config["complexity"]):
                    ax.add_patch(Arc((x, y), radius * 2, radius * 2,
                                     theta1=index * 360 / config["complexity"],
                                     theta2=index * 360 / config["complexity"] + 220 / config["complexity"],
                                     lw=3 * unit, color=color))
                    radius *= 0.82
            elif kind == 1:
                angles = np.linspace(0, 2 * np.pi, config["symmetry"], endpoint=False) + np.pi / 2
                points = np.column_stack((x + radius * np.cos(angles), y + radius * np.sin(angles)))
                ax.add_patch(Polygon(points, facecolor=color, edgecolor="none", alpha=0.85))
            else:
                ax.add_patch(Circle((x, y), radius, fill=False, edgecolor=color, lw=3 * unit))
                ax.add_patch(Circle((x, y), radius * 0.35, color=color, lw=0))


def phyllotaxis(ax, config, rng, unit):
    """Den gyldne vinkel skaber en spiral uden tilfældige positioner."""
    bx, by = _bounds(config)
    count = config["density"] * 22
    index = np.arange(1, count + 1)
    radius = np.sqrt(index / count)
    angle = index * np.pi * (3 - np.sqrt(5)) + rng.uniform(0, 2 * np.pi)
    angle += config["variation"] * 0.09 * np.sin(radius * config["complexity"] * np.pi)
    x, y = radius * np.cos(angle) * bx, radius * np.sin(angle) * by
    bands = ((radius * config["complexity"]).astype(int) + index % 3) % len(config["colors"])
    sizes = (3 + 7 * (1 - radius) ** 0.6) ** 2 * unit**2 * (1600 / count)
    if config["mode"] == "orbit":
        sizes *= 0.85
        for r in (0.3, 0.55, 0.8):
            theta = np.linspace(0, 2 * np.pi, 240)
            _lines(ax, [np.column_stack((r * bx * np.cos(theta), r * by * np.sin(theta)))],
                   [config["colors"][0]], unit * 0.6, 0.3)
    ax.scatter(x, y, s=sizes, c=np.array(config["colors"])[bands], edgecolors="none", alpha=0.9)


def flow(ax, config, rng, unit):
    """Et glat trigonometrisk vektorfelt leder alle kurver."""
    bx, by = _bounds(config)
    count = config["density"] * 9
    position = rng.uniform([-bx, -by], [bx, by], (count, 2))
    phases = rng.uniform(0, 2 * np.pi, 3)
    paths = [[] for _ in range(count)]
    active = np.ones(count, dtype=bool)
    frequency = 1.3 + config["complexity"] * 0.22
    for _ in range(110 + config["complexity"] * 16):
        x, y = position.T
        angle = (np.sin(x * frequency + phases[0]) + np.cos(y * frequency + phases[1]))
        angle *= 0.65 + config["variation"] * 1.7
        if config["mode"] == "vortex":
            angle += np.arctan2(y, x) + np.pi / 2
        elif config["mode"] == "vertical":
            angle += np.pi / 2
        position += 0.009 * np.column_stack((np.cos(angle), np.sin(angle)))
        active &= (abs(position[:, 0]) < bx) & (abs(position[:, 1]) < by)
        for index in np.flatnonzero(active):
            paths[index].append(position[index].copy())
    segments, colors, widths = [], [], []
    for path in paths:
        if len(path) > 4:
            segments.append(path)
            colors.append(config["colors"][rng.integers(len(config["colors"]))])
            widths.append(unit * rng.uniform(0.9, 2.1))
    _lines(ax, segments, colors, widths, 0.78)


def tree(ax, config, rng, unit):
    """Hver gren skaber to mindre grene, indtil dybden er nul."""
    bx, by = _bounds(config)
    segments, colors, widths, leaves = [], [], [], []
    depth = config["complexity"]
    spread = 0.27 + config["variation"] * 0.6

    def branch(x, y, angle, length, remaining):
        end = (x + math.cos(angle) * length, y + math.sin(angle) * length)
        segments.append([(x, y), end])
        colors.append(config["colors"][(depth - remaining) % len(config["colors"])])
        widths.append(unit * max(0.6, remaining * 0.7))
        if remaining > 0:
            for direction in (-1, 1):
                turn = direction * spread + rng.normal(0, config["variation"] * 0.09)
                branch(*end, angle + turn, length * rng.uniform(0.63, 0.73), remaining - 1)
        else:
            leaves.append(end)

    trunks = max(1, config["density"] // 25) if config["mode"] == "forest" else 1
    for x in np.linspace(-0.68, 0.68, trunks) if trunks > 1 else [0]:
        branch(x, -0.85, np.pi / 2, 0.54, depth)
    # Tilpas hele træet til formatet, inklusive de yderste blade.
    points = np.array(segments)
    low, high = points.reshape(-1, 2).min(0), points.reshape(-1, 2).max(0)
    scale = min(1.92 * bx / max(high[0] - low[0], 0.01), 1.92 * by / (high[1] - low[1]))
    center = (low + high) / 2
    _lines(ax, (points - center) * scale, colors, widths, 0.9)
    if leaves:
        leaf_array = (np.array(leaves) - center) * scale
        ax.scatter(*leaf_array.T, s=unit**2 * 4, c=config["colors"][-1], alpha=0.65, linewidths=0)


def fractal(ax, config, rng, unit):
    """Beregn flugttider i striber for at begrænse hukommelsesforbruget."""
    width, height = config["_render_width"], config["_render_height"]
    bx, by = _bounds(config)
    width = max(32, round(width * (1 - 2 * config["margin"])))
    height = max(32, round(height * (1 - 2 * config["margin"])))
    result = np.zeros((height, width), dtype=np.float32)
    iterations = 50 + 25 * config["complexity"]
    zoom = 1 if config["mode"] != "detail" else 0.23
    center_x = -0.65 if config["mode"] != "julia" else 0
    center_y = 0 if config["mode"] != "detail" else 0.48
    center_x += rng.uniform(-0.08, 0.08) * zoom
    center_y += rng.uniform(-0.08, 0.08) * zoom
    span_y = 1.35 * zoom
    xs = np.linspace(center_x - span_y * bx / by, center_x + span_y * bx / by, width)
    ys = np.linspace(center_y - span_y, center_y + span_y, height)
    julia_c = complex(-0.76 + config["variation"] * 0.12, 0.156 + rng.uniform(-0.012, 0.012))
    for start in range(0, height, 80):
        grid = xs[None, :] + 1j * ys[start:start + 80, None]
        z = grid.copy() if config["mode"] == "julia" else np.zeros_like(grid)
        c = julia_c if config["mode"] == "julia" else grid
        alive = np.ones(grid.shape, dtype=bool)
        values = np.zeros(grid.shape, dtype=np.float32)
        for step in range(iterations):
            z[alive] = z[alive] ** 2 + (c if np.isscalar(c) else c[alive])
            escaped = alive & (np.abs(z) > 4)
            values[escaped] = step + 1 - np.log2(np.log2(np.abs(z[escaped])))
            alive[escaped] = False
            if not alive.any():
                break
        result[start:start + len(grid)] = np.where(alive, 0, np.power(np.maximum(values, 0) / iterations, 0.32))
    cmap = LinearSegmentedColormap.from_list("atelier", [config["background"]] + config["colors"])
    rgba = cmap(result)
    if config["transparent"]:
        rgba[..., 3] = (result > 0).astype(float)
    ax.imshow(rgba, extent=(-bx, bx, -by, by), origin="lower", interpolation="nearest", aspect="auto")


def truchet(ax, config, rng, unit):
    """Tilfældige fliseorienteringer danner sammenhængende buer."""
    bx, by = _bounds(config)
    rows = 3 + config["density"] // 9
    cols = max(2, round(rows * bx / by))
    cell = min(2 * bx / cols, 2 * by / rows)
    for row in range(rows):
        for col in range(cols):
            x, y = (col - cols / 2) * cell, (row - rows / 2) * cell
            flip = rng.random() < (0.15 + config["variation"] * 0.7)
            corners = [(x, y, 0), (x + cell, y + cell, 180)] if flip else [(x, y + cell, 270), (x + cell, y, 90)]
            for cx, cy, start in corners:
                for band in range(max(1, config["complexity"] // 2)):
                    diameter = cell * (1 + (band - (config["complexity"] // 2 - 1) / 2) * 0.13)
                    color = config["colors"][band % len(config["colors"])]
                    ax.add_patch(Arc((cx, cy), diameter, diameter, theta1=start, theta2=start + 90,
                                     color=color, lw=unit * 1.3))


@dataclass
class Particle:
    position: np.ndarray
    velocity: np.ndarray
    color: str

    def step(self, center, strength):
        offset = self.position - center
        tangent = np.array([-offset[1], offset[0]])
        self.velocity = 0.94 * self.velocity + tangent * strength - offset * 0.001
        self.position = self.position + self.velocity
        return self.position.copy()


class Swarm:
    """Objekter bruger NumPy-vektorer og reagerer på et fælles centrum."""
    def __init__(self, particles):
        self.particles = particles

    def paths(self, steps, strength):
        paths = [[p.position.copy()] for p in self.particles]
        for _ in range(steps):
            center = np.mean([p.position for p in self.particles], axis=0)
            for particle, path in zip(self.particles, paths):
                path.append(particle.step(center, strength))
        return np.array(paths)


def particles(ax, config, rng, unit):
    bx, by = _bounds(config)
    objects = [Particle(rng.normal(0, 0.4, 2), rng.normal(0, 0.008, 2),
                        config["colors"][i % len(config["colors"])]) for i in range(config["density"] * 2)]
    paths = Swarm(objects).paths(config["complexity"] * 18, 0.002 + config["variation"] * 0.006)
    scale = np.max(np.abs(paths), axis=(0, 1)) + 0.02
    paths = paths / scale * [bx, by]
    _lines(ax, paths, [p.color for p in objects], unit * 1.5, 0.75)
    ax.scatter(*paths[:, -1].T, s=unit**2 * 20, c=[p.color for p in objects], linewidths=0)


SAMPLE_TEXT = """Blå bølger 12, grønne blade 34, gyldne spiraler 56.
Kode kan skabe kunst. Python forbinder mønstre, former og farver 2026.
Havets strømme gentager rytmer; skoven forgrener sine stier 89."""


def regex_art(ax, config, rng, unit):
    """Regex-fund afgør vævningens længder og farver."""
    bx, by = _bounds(config)
    pattern = r"\d+" if config["mode"] == "digits" else r"[^\W\d_]+"
    matches = re.findall(pattern, SAMPLE_TEXT, flags=re.UNICODE)
    offset = rng.integers(len(matches))
    count = config["density"] + 10
    segments, colors, widths = [], [], []
    for row in range(count):
        token = matches[(row + offset) % len(matches)]
        y = -by + (row + 0.5) * 2 * by / count
        pieces = 4 + len(token)
        for col in range(pieces):
            x = -bx + col * 2 * bx / pieces
            span = 2 * bx / pieces
            wave = np.linspace(0, 1, 18)
            path = np.column_stack((x + wave * span * 0.82,
                                     y + np.sin(wave * np.pi) * config["variation"] * 0.025))
            segments.append(path)
            colors.append(config["colors"][(ord(token[col % len(token)]) + row) % len(config["colors"])])
            widths.append(unit * (1 + len(token) % 4) * rng.uniform(0.5, 0.8))
    _lines(ax, segments, colors, widths, 0.85)


API_DATA = {"pages": [{"page": page, "items": [{"id": page * 10 + i, "value": (page + i) % 4}
                                               for i in range(5)]} for page in range(4)]}
USER_DATA = [{"id": i, "role": ("læser", "forfatter", "redaktør")[i % 3]} for i in range(24)]
GIT_DATA = [
    {"id": 0, "branch": 0, "parents": []},
    {"id": 1, "branch": 1, "parents": [0]},
    {"id": 2, "branch": -1, "parents": [0]},
    {"id": 3, "branch": 0, "parents": [0]},
    {"id": 4, "branch": 1, "parents": [1]},
    {"id": 5, "branch": -1, "parents": [2]},
    {"id": 6, "branch": 0, "parents": [3]},
    {"id": 7, "branch": 1, "parents": [4]},
    {"id": 8, "branch": -1, "parents": [5]},
    {"id": 9, "branch": 0, "parents": [6]},
    {"id": 10, "branch": 1, "parents": [7]},
    {"id": 11, "branch": -1, "parents": [8]},
    {"id": 12, "branch": 0, "parents": [9, 10]},
    {"id": 13, "branch": -1, "parents": [11]},
    {"id": 14, "branch": 0, "parents": [12, 13]},
    {"id": 15, "branch": 0, "parents": [14]},
]


def network_data(mode):
    """Data og arkitektur er adskilt fra selve tegningen."""
    if mode == "api":
        nodes = [(-0.95, 0)]
        edges = []
        for page in API_DATA["pages"]:
            parent = len(nodes)
            y = (page["page"] - 1.5) * 0.48
            nodes.append((-0.3, y))
            edges.append((0, parent))
            for item in page["items"]:
                child = len(nodes)
                nodes.append((0.38, y + (item["id"] % 10 - 2) * 0.055))
                edges.append((parent, child))
                nodes.append((0.94, (item["value"] - 1.5) * 0.45))
                edges.append((child, len(nodes) - 1))
        return np.array(nodes), edges
    if mode == "git":
        nodes = [(record["id"] / 15 * 1.9 - 0.95, record["branch"] * 0.48) for record in GIT_DATA]
        edges = [(parent, record["id"]) for record in GIT_DATA for parent in record["parents"] if parent >= 0]
        return np.array(nodes), edges
    nodes = [(0, 0)]
    edges = []
    for role in range(3):
        angle = role * 2 * np.pi / 3 + np.pi / 2
        center = np.array([np.cos(angle), np.sin(angle)]) * 0.57
        parent = len(nodes)
        nodes.append(center)
        edges.append((0, parent))
        members = [record for record in USER_DATA if record["id"] % 3 == role]
        for i, member in enumerate(members):
            angle = i * 2 * np.pi / len(members)
            nodes.append(center + [np.cos(angle) * 0.25, np.sin(angle) * 0.25])
            edges.append((parent, len(nodes) - 1))
    return np.array(nodes), edges


def network(ax, config, rng, unit):
    bx, by = _bounds(config)
    nodes, edges = network_data(config["mode"])
    nodes = nodes * [bx, by]
    nodes += rng.normal(0, 0.035 * config["variation"], nodes.shape)
    paths, colors = [], []
    for index, (a, b) in enumerate(edges):
        t = np.linspace(0, 1, 45)[:, None]
        start, end = nodes[a], nodes[b]
        control_a, control_b = np.array([end[0], start[1]]), np.array([start[0], end[1]])
        paths.append((1 - t)**3 * start + 3 * (1 - t)**2 * t * control_a + 3 * (1 - t) * t**2 * control_b + t**3 * end)
        colors.append(config["colors"][index % len(config["colors"])])
    _lines(ax, paths, colors, unit * 3, 0.8)
    node_colors = [config["colors"][i % len(config["colors"])] for i in range(len(nodes))]
    ax.scatter(*nodes.T, s=unit**2 * 550, c=node_colors, alpha=0.12, linewidths=0, zorder=2)
    ax.scatter(*nodes.T, s=unit**2 * 150, c=node_colors,
               edgecolors=config["background"], linewidths=unit * 1.3, zorder=3)


def kmeans(points, count, rng, iterations=30):
    """Lloyds algoritme: skift mellem tildeling og nye gennemsnit."""
    centers = points[rng.choice(len(points), count, replace=False)].copy()
    for _ in range(iterations):
        labels = np.argmin(((points[:, None] - centers) ** 2).sum(axis=2), axis=1)
        updated = np.array([points[labels == i].mean(0) if np.any(labels == i) else centers[i] for i in range(count)])
        if np.allclose(updated, centers):
            break
        centers = updated
    labels = np.argmin(((points[:, None] - centers) ** 2).sum(axis=2), axis=1)
    return labels, centers


def clusters(ax, config, rng, unit):
    bx, by = _bounds(config)
    count = min(config["complexity"], len(config["colors"]) + 2)
    centers = rng.uniform(-0.65, 0.65, (count, 2))
    points = np.concatenate([rng.normal(center, 0.06 + config["variation"] * 0.15,
                                        (config["density"] * 4, 2)) for center in centers])
    # Centrér punktlandskabet og brug pladsen, uanset tilfældige startcentre.
    low, high = np.quantile(points, [0.005, 0.995], axis=0)
    points = (points - (low + high) / 2) / np.maximum((high - low) / 2, 0.01) * [bx * 0.9, by * 0.9]
    labels, fitted = kmeans(points, count, rng)
    clipped = (abs(points[:, 0]) < bx) & (abs(points[:, 1]) < by)
    ax.scatter(*points[clipped].T, s=unit**2 * rng.uniform(7, 32, clipped.sum()),
               c=[config["colors"][i % len(config["colors"])] for i in labels[clipped]], alpha=0.85, linewidths=0)
    for index, center in enumerate(fitted):
        for radius in np.linspace(0.04, 0.18, 4):
            ax.add_patch(Circle(center, radius, fill=False, edgecolor=config["colors"][index % len(config["colors"])],
                                lw=unit * 1.2, alpha=0.5))


SAMPLE_HTML = """<main><section><h1>Haven</h1><article><h2>Blade</h2><p>Grøn</p><p>Guld</p></article>
<article><h2>Blomster</h2><p>Rose</p><p>Valmue</p><p>Viol</p></article></section>
<section><h1>Havet</h1><article><p>Bølge</p><p>Strøm</p></article></section></main>"""


class DocumentTree(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.nodes, self.edges = [], [], []

    def handle_starttag(self, tag, attrs):
        index = len(self.nodes)
        self.nodes.append((tag, len(self.stack)))
        if self.stack:
            self.edges.append((self.stack[-1], index))
        if tag not in {"br", "img", "hr", "input", "meta", "link"}:
            self.stack.append(index)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()


def html_art(ax, config, rng, unit):
    bx, by = _bounds(config)
    document = DocumentTree()
    document.feed(SAMPLE_HTML)
    positions = []
    maximum_depth = max(depth for _, depth in document.nodes)
    phase = rng.uniform(0, 2 * np.pi)
    for index, (tag, depth) in enumerate(document.nodes):
        angle = index / len(document.nodes) * 2 * np.pi + phase
        angle += np.sin(index * 1.7) * config["variation"] * 0.25
        radius = 0.16 + 0.8 * (depth / maximum_depth)**(0.6 + config["complexity"] * 0.07)
        positions.append([np.cos(angle) * radius * bx, np.sin(angle) * radius * by])
    positions = np.array(positions)
    paths = []
    for parent, child in document.edges:
        t = np.linspace(0, 1, 50)[:, None]
        paths.append((1 - t)**2 * positions[parent] + t**2 * positions[child])
    _lines(ax, paths, [config["colors"][i % len(config["colors"])] for i in range(len(paths))], unit * 2.2, 0.75)
    for pos, (tag, depth) in zip(positions, document.nodes):
        ax.add_patch(Circle(pos, 0.02 + 0.011 * (maximum_depth - depth),
                            color=config["colors"][depth % len(config["colors"])]))


RENDERERS = {"geometry": geometry, "phyllotaxis": phyllotaxis, "flow": flow, "tree": tree,
             "fractal": fractal, "truchet": truchet, "particles": particles, "regex": regex_art,
             "network": network, "clusters": clusters, "html": html_art}


def render(settings: dict, fmt="png", max_side=None) -> bytes:
    """Tegn i normaliserede koordinater; opløsning ændrer ikke tilfældighed eller layout."""
    config = validate_config(settings)
    if fmt not in {"png", "jpg", "jpeg", "svg", "pdf"}:
        raise ValueError("Vælg PNG, JPG, SVG eller PDF.")
    if fmt == "svg" and config["generator"] == "fractal":
        raise ValueError("Fraktaler er pixelbaserede. Vælg PNG eller PDF.")
    width, height = config["width"], config["height"]
    if max_side:
        ratio = min(1, max_side / max(width, height))
        width, height = max(1, round(width * ratio)), max(1, round(height * ratio))
    config["_render_width"], config["_render_height"] = width, height
    dpi = config["dpi"]
    # Næste repræsenterbare float undgår afrunding til én pixel for lidt i Agg.
    figsize = (np.nextafter(width / dpi, np.inf), np.nextafter(height / dpi, np.inf))
    with RENDER_LOCK, matplotlib.rc_context({"svg.hashsalt": str(config["seed"]), "path.simplify": False}):
        fig = Figure(figsize=figsize, dpi=dpi, facecolor=config["background"])
        FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        aspect = config["width"] / config["height"]
        ax.set(xlim=(-aspect, aspect), ylim=(-1, 1), aspect="equal")
        ax.set_axis_off()
        unit = min(width, height) / 800 * 72 / dpi * config["stroke"]
        rng = np.random.default_rng(config["seed"])
        try:
            RENDERERS[config["generator"]](ax, config, rng, unit)
            output = io.BytesIO()
            metadata = {"Date": None} if fmt == "svg" else ({"CreationDate": None, "ModDate": None} if fmt == "pdf" else {})
            raster_format = "png" if fmt in {"jpg", "jpeg"} else fmt
            fig.savefig(output, format=raster_format, dpi=dpi, transparent=config["transparent"],
                        facecolor="none" if config["transparent"] else config["background"],
                        bbox_inches=None, pad_inches=0, metadata=metadata)
            if fmt in {"png", "jpg", "jpeg"}:
                with Image.open(io.BytesIO(output.getvalue())) as check:
                    if check.size != (width, height):
                        raise RuntimeError(f"Forkerte pixelmål: {check.size}, forventede {(width, height)}.")
                    if fmt in {"jpg", "jpeg"}:
                        # JPEG har ingen alfakanal. Bevar den valgte baggrund, også ved transparens.
                        background = Image.new("RGBA", check.size, config["background"])
                        flattened = Image.alpha_composite(background, check.convert("RGBA")).convert("RGB")
                        output = io.BytesIO()
                        flattened.save(output, format="JPEG", quality=95, subsampling=0,
                                       optimize=True, dpi=(dpi, dpi))
            return output.getvalue()
        finally:
            fig.clear()
