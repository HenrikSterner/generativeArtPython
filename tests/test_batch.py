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

from atelier.batch import DEFAULT_FILENAMES, chapter_art_jobs, export_chapter_art
from atelier.catalog import preset_config
from atelier.core import render
from atelier.education import CHAPTERS


@pytest.mark.parametrize("size", [(2480, 1110), (3000, 1343)])
def test_chapter_art_dimensions_and_profiles(size):
    jobs = chapter_art_jobs(DEFAULT_FILENAMES, seed=314, size=size)
    assert len(jobs) == 15
    assert {job["chapter"] for job in jobs} == set(CHAPTERS)
    assert "chapter-13-webscrabing.jpg" in {job["filename"] for job in jobs}
    assert "chapter-11-arkitektur-for-dataudtraek-gennem-api.jpg" in {job["filename"] for job in jobs}
    for job in jobs:
        config = job["config"]
        assert (config["width"], config["height"]) == size
        assert config["dpi"] == 300 and config["margin"] >= 0.12
        assert config["transparent"] is False
        assert config["generator"] == CHAPTERS[job["chapter"]][1]
    image = Image.open(io.BytesIO(render(jobs[0]["config"], fmt="jpg")))
    assert image.size == size
    assert image.mode == "RGB" and image.format == "JPEG"
    assert image.info["dpi"] == (300, 300)


def test_sixteenth_variant_and_shared_style():
    filenames = DEFAULT_FILENAMES + "\nchapter-11-arkitektur-for-dataudtraek-gennem-api-variant.jpg"
    jobs = chapter_art_jobs(filenames, book_palette="Nordisk")
    assert len(jobs) == 16
    variants = [job for job in jobs if job["chapter"] == 11]
    assert len({job["config"]["seed"] for job in variants}) == 2
    assert all(job["config"]["palette"] == "Nordisk" for job in jobs)
    assert chapter_art_jobs(filenames, book_palette="Nordisk") == jobs


@pytest.mark.parametrize("names", [
    DEFAULT_FILENAMES + "\n" + DEFAULT_FILENAMES.splitlines()[0],
    DEFAULT_FILENAMES.replace("chapter-01-dit-foerste-program.jpg", "../chapter-01-dit-foerste-program.jpg"),
    DEFAULT_FILENAMES.replace("chapter-01-dit-foerste-program.jpg", "chapter-02-variant.jpg"),
    DEFAULT_FILENAMES.replace(".jpg", ".png"),
])
def test_invalid_batch_filenames_rejected(names):
    with pytest.raises(ValueError):
        chapter_art_jobs(names)


def test_jpg_flattens_alpha_on_selected_background():
    config = preset_config("tree", "Herbarium")
    config.update(width=320, height=180, transparent=True, background="#193e52")
    image = Image.open(io.BytesIO(render(config, fmt="jpeg")))
    assert image.mode == "RGB"
    assert np.max(np.abs(np.array(image.getpixel((0, 0))) - [25, 62, 82])) <= 2


def test_archive_and_reproduction_without_app(tmp_path):
    jobs = chapter_art_jobs(DEFAULT_FILENAMES)
    # En lille udgave af hele serien holder processen hurtig og tester alle generatorer.
    for job in jobs:
        job["config"].update(width=360, height=161)
    progress = []
    data = export_chapter_art(jobs, lambda fraction, message: progress.append(fraction))
    assert progress[0] == 0 and progress[-1] == 1
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert len([name for name in archive.namelist() if name.endswith(".jpg")]) == 15
        assert len([name for name in archive.namelist() if name.startswith("code/")]) == 15
        manifest = json.loads(archive.read("manifest.json"))
        assert len(manifest["images"]) == 15
        expected = {job["filename"]: archive.read(job["filename"]) for job in jobs}
        for job in jobs:
            assert Image.open(io.BytesIO(expected[job["filename"]])).size == (360, 161)
            assert json.loads(archive.read(job["settings"]))["settings"] == job["config"]
        archive.extractall(tmp_path / "unpacked")
    # Flyt originalerne væk: scriptet skal faktisk skabe nye filer.
    for filename in expected:
        (tmp_path / "unpacked" / filename).unlink()
    result = subprocess.run([sys.executable, str(tmp_path / "unpacked" / "generate_all.py")],
                            cwd=tmp_path, env=dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8"),
                            capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert result.returncode == 0, result.stderr
    for filename, content in expected.items():
        assert (tmp_path / "unpacked" / filename).read_bytes() == content
    # Enkeltfilen skal også vælge det rigtige JPG-filnavn uden CLI-argumenter.
    result = subprocess.run([sys.executable, str(tmp_path / "unpacked" / jobs[0]["code"])],
                            cwd=tmp_path, env=dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8"),
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / jobs[0]["filename"]).read_bytes() == expected[jobs[0]["filename"]]
