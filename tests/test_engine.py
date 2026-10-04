import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image
import pytest

from atelier.catalog import GENERATORS, THEMES, apply_book_style, interpret_theme, preset_config
from atelier.core import kmeans, render, validate_config
from atelier.education import CHAPTERS, chapter_config, teaching_code
from atelier.exports import export_bundle, load_settings, settings_json, standalone_code
from atelier.ui_state import cm_to_pixels, pixels_to_cm


PRESETS = [(generator, name) for generator, values in GENERATORS.items() for name in values["presets"]]


def small_config(generator="flow", preset=None):
    config = preset_config(generator, preset or next(iter(GENERATORS[generator]["presets"])))
    config.update(width=361, height=247, dpi=300)
    return config


@pytest.mark.parametrize("generator,preset", PRESETS)
def test_every_preset_produces_exact_size_and_visible_art(generator, preset):
    image = Image.open(io.BytesIO(render(small_config(generator, preset))))
    assert image.size == (361, 247)
    pixels = np.asarray(image.convert("RGB"))
    assert len(np.unique(pixels.reshape(-1, 3), axis=0)) > 40
    assert (np.any(pixels != pixels[0, 0], axis=2)).mean() > 0.015


@pytest.mark.parametrize("number", CHAPTERS)
def test_chapter_preset_and_teaching_example(number, tmp_path, monkeypatch):
    config = chapter_config(number)
    config.update(width=320, height=240)
    assert Image.open(io.BytesIO(render(config))).size == (320, 240)
    assert len(CHAPTERS[number][4]) == 3
    monkeypatch.chdir(tmp_path)
    exec(compile(teaching_code(number), f"chapter_{number}.py", "exec"), {"__name__": "__main__"})
    assert Image.open("undervisning.png").size == (600, 600)


@pytest.mark.parametrize("generator", GENERATORS)
def test_exported_script_runs_without_project_and_matches_pixels(generator, tmp_path):
    config = small_config(generator)
    expected = render(config)
    script = tmp_path / "kunst.py"
    script.write_text(standalone_code(config), encoding="utf-8")
    environment = dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, str(script), "--output", "actual.png"], cwd=tmp_path,
                            env=environment, capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert result.returncode == 0, result.stderr
    actual = Image.open(tmp_path / "actual.png")
    assert np.array_equal(np.asarray(actual), np.asarray(Image.open(io.BytesIO(expected))))


@pytest.mark.parametrize("generator", GENERATORS)
def test_render_is_repeatable(generator):
    config = small_config(generator)
    assert render(config) == render(config)


@pytest.mark.parametrize("generator", GENERATORS)
def test_new_seed_changes_each_generator(generator):
    config = small_config(generator)
    previous = render(config)
    config["seed"] += 1
    assert render(config) != previous


@pytest.mark.parametrize("width,height,dpi", [(800, 800, 300), (1600, 900, 300), (1920, 1080, 96),
                                               (2400, 2400, 300), (2480, 3508, 300), (3508, 2480, 300),
                                               (101, 203, 72), (999, 777, 600)])
def test_required_export_dimensions(width, height, dpi):
    config = small_config("geometry")
    config.update(width=width, height=height, dpi=dpi)
    image = Image.open(io.BytesIO(render(config)))
    assert image.size == (width, height)
    assert abs(image.info["dpi"][0] - dpi) < 0.03


@pytest.mark.parametrize("generator", [key for key in GENERATORS if key != "fractal"])
def test_svg_contains_vectors_not_embedded_raster(generator):
    svg = render(small_config(generator), fmt="svg").decode()
    assert "<path" in svg
    assert "<image" not in svg


def test_transparency_and_fractal_formats():
    config = small_config("fractal", "Julia")
    config["transparent"] = True
    alpha = np.asarray(Image.open(io.BytesIO(render(config))))[:, :, 3]
    assert alpha.min() == 0 and alpha.max() == 255
    assert render(config, fmt="pdf").startswith(b"%PDF")
    with pytest.raises(ValueError, match="pixelbaserede"):
        render(config, fmt="svg")


def test_settings_round_trip_and_zip_matches():
    config = small_config("network", "Datastrømme")
    config.update(chapter=11, theme_text="havstrømme", seed=1895, transparent=True)
    assert load_settings(settings_json(config)) == config
    files, bundle = export_bundle(config)
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == set(files)
        assert load_settings(archive.read("indstillinger.json")) == config
        assert archive.read("kunst.png") == render(config)
        assert archive.read("kunst.pdf").startswith(b"%PDF")


@pytest.mark.parametrize("patch", [
    {"width": 0}, {"width": 9000}, {"width": 8000, "height": 8000}, {"seed": -1},
    {"seed": True}, {"density": 1000}, {"colors": ["red", "blue"]},
    {"variation": float("nan")}, {"generator": "unknown"}, {"theme": []},
    {"transparent": "false"}, {"colors": "#ffffff"}, {"background": "<script>"},
    {"schema_version": 2},
])
def test_invalid_import_rejected(patch):
    config = small_config()
    config.update(patch)
    with pytest.raises(ValueError):
        load_settings(json.dumps(config))


@pytest.mark.parametrize("payload", ["[]", "null", "invalid", '{"settings": null}'])
def test_malformed_documents_rejected(payload):
    with pytest.raises(ValueError):
        load_settings(payload)


@pytest.mark.parametrize("theme", THEMES)
def test_themes_change_image_beyond_label(theme):
    config = small_config("flow")
    baseline = render(config)
    patch, description, notice = interpret_theme(theme)
    patch.pop("generator")
    config.update(patch)
    assert render(config) != baseline
    assert description and notice


def test_freetext_and_book_style():
    patch, _, notice = interpret_theme("Havstrømme", "rekursion som et koralrev")
    assert patch["generator"] == "tree"
    assert "koral" in notice
    _, _, notice = interpret_theme("Havstrømme", "xyzabc")
    assert "Ingen kendte" in notice
    first = apply_book_style(chapter_config(1), "Sort-hvid")
    second = apply_book_style(chapter_config(15), "Sort-hvid")
    for key in ("colors", "background", "stroke", "margin"):
        assert first[key] == second[key]


def test_print_conversions_and_actual_learning():
    assert cm_to_pixels(21, 300) == 2480
    assert cm_to_pixels(pixels_to_cm(3508, 300), 300) == 3508
    points = np.array([[-10., 0], [-9, 0], [9, 0], [10, 0]])
    labels, centers = kmeans(points, 2, np.random.default_rng(42))
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]
    assert np.allclose(sorted(centers[:, 0]), [-9.5, 9.5])
