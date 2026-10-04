"""Eksportér præcis den kode, tegneappen selv bruger."""

import ast
import hashlib
import importlib.metadata
import inspect
import io
import json
import platform
import zipfile

from atelier import __version__, core
from atelier.catalog import validate_catalog_config
from atelier.education import caption, teaching_code


def versions():
    return {"python": platform.python_version(), **{name: importlib.metadata.version(name)
            for name in ("numpy", "matplotlib", "Pillow", "streamlit")}}


def settings_json(config):
    config = validate_catalog_config(config)
    document = {"app_version": __version__, "versions": versions(),
                "engine_sha256": hashlib.sha256(inspect.getsource(core).encode()).hexdigest(),
                "settings": config}
    return json.dumps(document, ensure_ascii=False, indent=2)


def load_settings(data):
    if len(data) > 2_000_000:
        raise ValueError("Indstillingsfilen må højst fylde 2 MB.")
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Filen indeholder ikke gyldig JSON.") from error
    if not isinstance(document, dict):
        raise ValueError("JSON-filen skal indeholde et objekt med indstillinger.")
    return validate_catalog_config(document.get("settings", document))


def standalone_code(config, default_output="kunst.png"):
    """Udvælg generatorens faktiske funktioner med deres transitive afhængigheder."""
    config = validate_catalog_config(config)
    source = inspect.getsource(core)
    module = ast.parse(source)
    definitions, imports, order = {}, [], []
    for node in module.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.get_source_segment(source, node))
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            # get_source_segment udelader dekoratoren på dataclasses.
            first_line = min([node.lineno] + [d.lineno for d in node.decorator_list])
            code = "\n".join(source.splitlines()[first_line - 1:node.end_lineno])
            definitions[node.name] = (node, code)
            order.append(node.name)
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            definitions[name] = (node, ast.get_source_segment(source, node))
            order.append(name)
    renderer_name = core.RENDERERS[config["generator"]].__name__
    registry = f"RENDERERS = {{{config['generator']!r}: {renderer_name}}}"
    definitions["RENDERERS"] = (ast.parse(registry).body[0], registry)
    needed, pending = set(), ["render"]
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        needed.add(name)
        node = definitions[name][0]
        pending.extend(child.id for child in ast.walk(node)
                       if isinstance(child, ast.Name) and child.id in definitions and child.id not in needed)
    dependencies = versions()
    installation = " ".join(f"{name}=={dependencies[name]}" for name in ("numpy", "matplotlib", "Pillow"))
    header = ("# Genereret af Python Atelier — komplet, selvstændig kunstgenerator.\n"
              f"# Python-version ved eksport: {dependencies['python']}\n"
              f"# Installer: python -m pip install {installation}\n"
              f"# Kør: python {default_output.rsplit('.', 1)[0]}.py\n"
              "# Brug --output filnavn.jpg for JPG; også PNG, PDF og SVG (fraktaler: PNG/JPG/PDF).\n"
              "# Koden nedenfor er hentet direkte fra appens tegnemotor.\n\n")
    selected = "\n\n\n".join(definitions[name][1] for name in order if name in needed)
    serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)
    footer = f'''


import argparse
import json
from pathlib import Path

# De præcise indstillinger for dette værk, inklusive seed og pixelmål.
SETTINGS = json.loads({serialized!r})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genskab kunstværket fra Python Atelier.")
    parser.add_argument("--output", default={default_output!r}, help="Filnavn med .png, .jpg, .pdf eller .svg")
    args = parser.parse_args()
    destination = Path(args.output)
    file_format = destination.suffix.lower().lstrip(".")
    destination.write_bytes(render(SETTINGS, fmt=file_format))
    print(f"Gemt: {{destination}} ({{SETTINGS['width']}} × {{SETTINGS['height']}} pixels)")
'''
    return header + "\n".join(imports) + "\n\n\n" + selected + footer


def export_bundle(config, progress=None):
    config = validate_catalog_config(config)
    files = {
        "kunst.py": standalone_code(config).encode("utf-8"),
        "indstillinger.json": settings_json(config).encode("utf-8"),
        "figurtekst.txt": caption(config).encode("utf-8"),
        "undervisning.py": teaching_code(config["chapter"]).encode("utf-8"),
    }
    formats = ["png", "pdf"] + ([] if config["generator"] == "fractal" else ["svg"])
    for index, fmt in enumerate(formats):
        if progress:
            progress(index / len(formats), f"Tegner {fmt.upper()} i {config['width']} × {config['height']} …")
        files[f"kunst.{fmt}"] = core.render(config, fmt=fmt)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    if progress:
        progress(1.0, "Alle filer er klar.")
    return files, buffer.getvalue()
