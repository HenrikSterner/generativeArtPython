"""Samlet eksport af bogens kapitelillustrationer og deres selvstændige kode."""

import io
import json
import re
from pathlib import PurePosixPath
import zipfile

from atelier.catalog import apply_book_style, validate_catalog_config
from atelier.core import render
from atelier.education import CHAPTERS, chapter_config
from atelier.exports import settings_json, standalone_code, versions


CHAPTER_ART_SIZES = {"2480 × 1110 px": (2480, 1110), "3000 × 1343 px": (3000, 1343)}
DEFAULT_FILENAMES = """chapter-01-dit-foerste-program.jpg
chapter-02-variabler-og-deres-datatyper.jpg
chapter-03-forgreninger-betinget-udfoerelse.jpg
chapter-04-loekker-og-lister.jpg
chapter-05-funktioner.jpg
chapter-06-rekursion.jpg
chapter-07-objektorienteret-programmering.jpg
chapter-08-oop-og-biblioteker-i-praksis.jpg
chapter-09-regulaere-udtryk.jpg
chapter-10-arkitektur-for-brugerhaandtering.jpg
chapter-11-arkitektur-for-dataudtraek-gennem-api.jpg
chapter-12-maskinlaering.jpg
chapter-13-webscrabing.jpg
chapter-14-test-i-python.jpg
chapter-15-samarbejde-gennem-github.jpg"""


def chapter_art_jobs(filenames, seed=42, size=(2480, 1110), book_palette=None):
    """Kapitelnummer i filnavnet vælger profil; gentagne numre får egne seeds."""
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seriens seed skal være et heltal mellem 0 og 4294967295.")
    if tuple(size) not in CHAPTER_ART_SIZES.values():
        raise ValueError("Vælg 2480 × 1110 eller 3000 × 1343 pixels til chapter-art.")
    names = [name.strip() for name in filenames.splitlines() if name.strip()]
    if not 15 <= len(names) <= 30:
        raise ValueError("Angiv 15–30 JPG-filnavne, mindst ét for hvert kapitel 01–15.")
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Hvert filnavn skal være unikt; to varianter skal have forskellige navne.")
    jobs, counts = [], {}
    for name in names:
        match = re.fullmatch(r"chapter-(0[1-9]|1[0-5])-[a-z0-9]+(?:-[a-z0-9]+)*\.jpg", name)
        if not match:
            raise ValueError(f"Ugyldigt filnavn: {name}. Brug chapter-01-titel.jpg med små ASCII-bogstaver.")
        chapter = int(match.group(1))
        variant = counts.get(chapter, 0)
        counts[chapter] = variant + 1
        config = chapter_config(chapter)
        if book_palette:
            config = apply_book_style(config, book_palette)
        config.update(width=size[0], height=size[1], dpi=300, transparent=False,
                      seed=(seed + chapter * 1009 + variant * 9176) % 2**32,
                      margin=max(0.12, config["margin"]))
        # Brug et motivsvarende tema i metadata, når kapitlets eget preset anvendes.
        config["theme"] = {
            "geometry": "Geometrisk arkitektur", "phyllotaxis": "Botaniske strukturer",
            "truchet": "Tekstilkunst", "tree": "Botaniske strukturer",
            "particles": "Kosmiske landskaber", "regex": "Tekstilkunst",
            "network": "Digitale netværk", "clusters": "Øer af datapunkter",
            "html": "Digitale netværk",
        }[config["generator"]]
        stem = PurePosixPath(name).stem
        jobs.append({"filename": name, "code": f"code/{stem}.py", "settings": f"settings/{stem}.json",
                     "chapter": chapter, "title": CHAPTERS[chapter][0], "variant": variant + 1,
                     "config": validate_catalog_config(config)})
    missing = sorted(set(CHAPTERS) - set(counts))
    if missing:
        raise ValueError("Filnavnelisten mangler kapitler: " + ", ".join(f"{number:02d}" for number in missing))
    return jobs


def batch_identity(jobs, engine_signature):
    """Eksporten er kun gyldig for den aktuelle serie, størrelse og tegnemotor."""
    return json.dumps({"jobs": jobs, "engine": engine_signature}, sort_keys=True, ensure_ascii=False)


def _runner_source(entries):
    """Start alle selvstændige generatorer, også fra en anden arbejdsmappe."""
    tasks = [(entry["code"], entry["filename"]) for entry in entries]
    return f'''# Genskab alle kapitelbilleder med samme filnavne og indstillinger.
# Installer først: python -m pip install -r requirements.txt
# Kør: python generate_all.py
from pathlib import Path
import subprocess
import sys

TASKS = {tasks!r}

if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    for index, (script, filename) in enumerate(TASKS, start=1):
        print(f"[{{index}}/{{len(TASKS)}}] {{filename}}", flush=True)
        subprocess.run([sys.executable, str(folder / script), "--output", str(folder / filename)],
                       cwd=folder, check=True)
    print("Alle kapitelbilleder er genskabt.")
'''


def export_chapter_art(jobs, progress=None):
    """Render sekventielt: kun ét ukomprimeret billede i hukommelsen ad gangen."""
    if not jobs:
        raise ValueError("Der er ingen kapitelbilleder at generere.")
    buffer = io.BytesIO()
    entries = []
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, job in enumerate(jobs):
            config = validate_catalog_config(job["config"])
            if progress:
                progress(index / len(jobs), f"{index + 1}/{len(jobs)} · {job['filename']}")
            archive.writestr(job["filename"], render(config, fmt="jpg"))
            archive.writestr(job["code"], standalone_code(config, default_output=job["filename"]).encode("utf-8"))
            archive.writestr(job["settings"], settings_json(config).encode("utf-8"))
            entries.append({key: job[key] for key in ("filename", "code", "settings", "chapter", "title", "variant")} |
                           {"seed": config["seed"], "width": config["width"], "height": config["height"],
                            "dpi": config["dpi"], "margin": config["margin"]})
        manifest = {"format": "JPEG", "quality": 95, "subsampling": 0, "versions": versions(), "images": entries}
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        archive.writestr("generate_all.py", _runner_source(entries).encode("utf-8"))
        dependencies = versions()
        archive.writestr("requirements.txt", "\n".join(f"{name}=={dependencies[name]}" for name in ("numpy", "matplotlib", "Pillow")) + "\n")
        archive.writestr("README.txt", (
            f"Python Atelier — {len(entries)} kapitelillustrationer\n\n"
            "JPG-billederne ligger i denne mappe. Kopiér dem direkte til bogens billedmappe.\n"
            "Hvert billede har en selvstændig generator i code/ og indstillinger i settings/.\n"
            "Filnavne, seeds og dimensioner er samlet i manifest.json.\n\n"
            "Genskab hele serien efter udpakning:\n"
            "  python -m pip install -r requirements.txt\n"
            "  python generate_all.py\n\n"
            "Kør en enkelt fil fra code/ for at genskabe dens JPG med det samme navn,\n"
            "eller brug --output til at vælge en anden placering.\n"
            "Generatorerne kræver hverken Streamlit eller det oprindelige projekt.\n\n"
            "Format: cirka 2,234:1, 300 DPI, JPEG-kvalitet 95 uden farveundersampling.\n"
            "Mindst 12 % kompositionsmargin på hver side giver plads til minimal cover-beskæring.\n"
        ).encode("utf-8"))
    if progress:
        progress(1.0, f"Alle {len(entries)} kapitelbilleder og Python-filer er klar.")
    return buffer.getvalue()
