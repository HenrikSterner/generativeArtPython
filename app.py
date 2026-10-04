"""Start med: python -m streamlit run app.py"""

from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
import secrets

import streamlit as st

from atelier.batch import (CHAPTER_ART_SIZES, DEFAULT_FILENAMES, batch_identity,
                           chapter_art_jobs, export_chapter_art)
from atelier.catalog import (GENERATORS, PALETTES, THEMES, apply_book_style,
                             interpret_theme, preset_config)
from atelier.core import DEFAULTS, render, validate_config
from atelier.education import CHAPTERS, caption, chapter_config, chapter_sources, teaching_code
from atelier.exports import export_bundle, load_settings, settings_json, standalone_code
from atelier.ui_state import SIZE_PRESETS, checked_dimensions, cm_to_pixels, pixels_to_cm


st.set_page_config(page_title="Python Atelier · Kunst til bogen", page_icon="◒", layout="wide")

CSS = """
<style>
.block-container {max-width:1480px;padding-top:4.5rem;padding-bottom:3rem;}
h1,h2,h3 {font-family:Georgia,'Times New Roman',serif!important;font-weight:400!important;}
h1 {font-size:3.2rem!important;letter-spacing:-.045em!important;line-height:1.12!important;}
h2 {letter-spacing:-.025em!important;}
[data-testid="stSidebar"] {border-right:1px solid #dedbd0;}
[data-testid="stSidebar"] .block-container {padding-top:1.5rem;}
.eyebrow {font-size:.68rem;letter-spacing:.2em;font-weight:650;color:#877965;margin-bottom:.75rem;}
.intro {max-width:680px;color:#69706a;font-size:1rem;line-height:1.65;margin:.35rem 0 1.5rem;}
.brand {font-family:Georgia,serif;font-size:1.6rem;letter-spacing:-.06em;margin-bottom:.15rem;}
.brand span {color:#b44e35;}
.side-note {color:#778079;font-size:.78rem;margin-bottom:1.8rem;}
.section-label {font-size:.7rem;text-transform:uppercase;letter-spacing:.13em;color:#8f7963;margin:1.3rem 0 .6rem;}
.art-meta {font-size:.72rem;text-transform:uppercase;letter-spacing:.13em;color:#807c70;padding:1rem 0;}
.swatches {display:flex;gap:7px;margin:.8rem 0 1rem;}
.swatch {width:30px;height:30px;border-radius:50%;border:1px solid #0000000b;}
.note {font-size:.84rem;line-height:1.7;color:#717970;}
.chapter-number {font-family:Georgia,serif;font-size:4rem;color:#b8b8a6;line-height:1;}
.chapter-label {font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;color:#8a8c7c;margin-top:.5rem;}
[data-testid="stImage"] {background:#eae7de;padding:14px;border:1px solid #e0dccf;border-radius:4px;}
[data-testid="stImage"] img {max-height:640px;object-fit:contain;}
[data-baseweb="tab-list"] {gap:1.4rem;border-bottom:1px solid #dedbd0;}
[data-baseweb="tab"] {font-size:.87rem;padding-bottom:.8rem;}
.footer {border-top:1px solid #dedbd0;margin-top:2.5rem;padding-top:1rem;color:#8b8e81;font-size:.73rem;letter-spacing:.04em;}
@media (max-width:640px) {
  .block-container {padding-left:1rem;padding-right:1rem;}
  h1 {font-size:2.5rem!important;}
  .intro {font-size:.9rem;}
  .chapter-number {font-size:2.2rem;}
  [data-testid="stImage"] {padding:6px;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def sync_print_size():
    state = st.session_state
    state["cm_width"] = pixels_to_cm(state["width"], state["dpi"])
    state["cm_height"] = pixels_to_cm(state["height"], state["dpi"])


def copy_settings(config, preserve=()):
    for key, value in config.items():
        if key in DEFAULTS and key not in preserve:
            st.session_state[key] = deepcopy(value)
    sync_print_size()
    st.session_state["aspect_ratio"] = st.session_state["width"] / st.session_state["height"]


def chapter_changed():
    number = st.session_state["chapter"]
    if number:
        copy_settings(chapter_config(number), preserve=("seed", "width", "height", "dpi", "book_style", "transparent", "theme", "theme_text"))
        st.session_state["theme_applied"] = False


def generator_changed():
    generator = st.session_state["generator"]
    first = next(iter(GENERATORS[generator]["presets"]))
    copy_settings(preset_config(generator, first), preserve=("chapter", "seed", "width", "height", "dpi", "theme", "theme_text", "book_style", "transparent"))
    st.session_state["theme_applied"] = False


def preset_changed():
    copy_settings(preset_config(st.session_state["generator"], st.session_state["preset"]),
                  preserve=("chapter", "seed", "width", "height", "dpi", "theme", "theme_text", "book_style", "transparent"))
    st.session_state["theme_applied"] = False


def theme_changed():
    state = st.session_state
    patch, _, _ = interpret_theme(state["theme"], state["theme_text"])
    if state["chapter"] == 0 and patch["generator"] != state["generator"]:
        state["generator"] = patch["generator"]
        generator_changed()
    for key, value in patch.items():
        if key != "generator":
            state[key] = deepcopy(value)
    state["theme_applied"] = True


def palette_changed():
    st.session_state.update(deepcopy(PALETTES[st.session_state["palette"]]))


def size_preset_changed():
    state = st.session_state
    state["width"], state["height"] = SIZE_PRESETS[state["size_preset"]]
    state["aspect_ratio"] = state["width"] / state["height"]
    sync_print_size()


def lock_changed():
    st.session_state["aspect_ratio"] = st.session_state["width"] / st.session_state["height"]


def dimension_changed(axis):
    state = st.session_state
    if state["lock_ratio"]:
        other = "height" if axis == "width" else "width"
        proposed = round(state[axis] / state["aspect_ratio"] if axis == "width" else state[axis] * state["aspect_ratio"])
        try:
            checked_dimensions(state[axis], proposed)
        except ValueError as error:
            state["dimension_notice"] = str(error)
            state[axis] = round(state[other] * state["aspect_ratio"] if axis == "width" else state[other] / state["aspect_ratio"])
        else:
            state[other] = proposed
    sync_print_size()


def centimeters_changed(axis):
    state = st.session_state
    width = cm_to_pixels(state["cm_width"], state["dpi"])
    height = cm_to_pixels(state["cm_height"], state["dpi"])
    if state["lock_ratio"]:
        if axis == "width":
            height = round(width / state["aspect_ratio"])
        else:
            width = round(height * state["aspect_ratio"])
    try:
        checked_dimensions(width, height)
        state["width"], state["height"] = width, height
    except ValueError as error:
        state["dimension_notice"] = str(error)
    sync_print_size()


def swap_dimensions():
    state = st.session_state
    state["width"], state["height"] = state["height"], state["width"]
    state["aspect_ratio"] = state["width"] / state["height"]
    sync_print_size()


def new_seed():
    st.session_state["seed"] = secrets.randbelow(2**32)


def import_settings():
    upload = st.session_state.get("settings_upload")
    if upload:
        try:
            config = load_settings(upload.getvalue())
            copy_settings(config)
            st.session_state["book_palette"] = config["palette"]
            st.session_state["theme_applied"] = False
            st.session_state["import_notice"] = "Indstillingerne er indlæst, inklusive seed og pixelmål."
        except (ValueError, TypeError) as error:
            st.session_state["import_notice"] = f"Filen kunne ikke indlæses: {error}"


ENGINE_SIGNATURE = hashlib.sha256((Path(__file__).parent / "atelier" / "core.py").read_bytes()).hexdigest()


@st.cache_data(show_spinner=False, max_entries=12)
def preview_image(config, engine_signature):
    return render(config, max_side=1100)


@st.cache_data(show_spinner=False, max_entries=16)
def exported_code(config, engine_signature):
    return standalone_code(config)


if "initialized" not in st.session_state:
    copy_settings(preset_config("flow", "Tidevand"))
    st.session_state.update(initialized=True, lock_ratio=False, book_palette="Nordisk",
                            size_preset=next(iter(SIZE_PRESETS)), theme_applied=False)

with st.sidebar:
    st.markdown('<div class="brand"><span>◒</span> Python Atelier</div><div class="side-note">Et værksted for kode og komposition.</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">01 / Retning</div>', unsafe_allow_html=True)
    st.selectbox("Kapitel", [0] + list(CHAPTERS), key="chapter", on_change=chapter_changed,
                 format_func=lambda number: "Fri kunst" if not number else f"{number:02d} · {CHAPTERS[number][0]}")
    st.selectbox("Tema", list(THEMES), key="theme", on_change=theme_changed)
    st.text_area("Tema med egne ord", key="theme_text", height=75, max_chars=2000,
                 placeholder="Fx rekursion som et koralrev …", on_change=theme_changed)
    st.button("Anvend tema", on_click=theme_changed, width="stretch")
    st.caption("Kapitelvalg bevarer kapitlets algoritme, når du anvender et tema.")

    st.markdown('<div class="section-label">02 / Komposition</div>', unsafe_allow_html=True)
    st.selectbox("Generator", list(GENERATORS), key="generator", on_change=generator_changed,
                 format_func=lambda key: GENERATORS[key]["name"])
    st.selectbox("Preset", list(GENERATORS[st.session_state["generator"]]["presets"]), key="preset", on_change=preset_changed)
    st.selectbox("Farvepalette", list(PALETTES), key="palette", on_change=palette_changed)
    st.color_picker("Baggrund", key="background", disabled=st.session_state["book_style"])
    st.toggle("Fælles bogstil", key="book_style", help="Deler palette, baggrund, margin og linjeudtryk på tværs af kapitler.")
    st.selectbox("Bogpalette", list(PALETTES), key="book_palette", disabled=not st.session_state["book_style"])

    controls = {
        "geometry": ["density", "complexity", "symmetry", "variation"],
        "phyllotaxis": ["density", "complexity", "variation"],
        "flow": ["density", "complexity", "variation"],
        "tree": ["density", "complexity", "variation"],
        "fractal": ["complexity", "variation"],
        "truchet": ["density", "complexity", "variation"],
        "particles": ["density", "complexity", "variation"],
        "regex": ["density", "variation"], "network": ["variation"],
        "clusters": ["density", "complexity", "variation"], "html": ["complexity", "variation"],
    }
    with st.expander("Form og detaljer", expanded=False):
        # Alle felter opretholdes, også når deres widget er skjult for generatoren.
        for key in ("density", "complexity", "symmetry", "variation"):
            st.session_state[key] = st.session_state[key]
        visible = controls[st.session_state["generator"]]
        if "density" in visible:
            st.slider("Tæthed", 5, 100, key="density")
        if "complexity" in visible:
            st.slider("Dybde / kompleksitet", 2, 10, key="complexity")
        if "symmetry" in visible:
            st.slider("Symmetri", 2, 16, key="symmetry")
        if "variation" in visible:
            st.slider("Variation", 0.0, 1.0, step=0.01, key="variation")
        st.slider("Linjer og punkter", 0.3, 3.0, step=0.1, key="stroke", disabled=st.session_state["book_style"])
        st.slider("Margin", 0.02, 0.25, step=0.01, key="margin", disabled=st.session_state["book_style"])

    st.number_input("Seed", min_value=0, max_value=2**32 - 1, step=1, key="seed")
    st.button("↻  Ny variation", on_click=new_seed, width="stretch", type="primary")

    st.markdown('<div class="section-label">03 / Format</div>', unsafe_allow_html=True)
    st.selectbox("Størrelsespreset", list(SIZE_PRESETS), key="size_preset", on_change=size_preset_changed)
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Bredde · px", 64, 8000, step=1, key="width", on_change=dimension_changed, args=("width",))
    with col2:
        st.number_input("Højde · px", 64, 8000, step=1, key="height", on_change=dimension_changed, args=("height",))
    st.checkbox("Lås billedformat", key="lock_ratio", on_change=lock_changed)
    st.button("⇄  Ombyt bredde og højde", on_click=swap_dimensions, width="stretch")
    st.checkbox("Transparent baggrund", key="transparent")
    with st.expander("Trykstørrelse og DPI"):
        st.number_input("DPI", 72, 600, step=1, key="dpi", on_change=sync_print_size)
        st.number_input("Bredde · cm", min_value=0.1, step=0.1, format="%.2f", key="cm_width", on_change=centimeters_changed, args=("width",))
        st.number_input("Højde · cm", min_value=0.1, step=0.1, format="%.2f", key="cm_height", on_change=centimeters_changed, args=("height",))
        st.caption("Ændr centimeter for at beregne nye pixelmål. DPI alene bevarer pixelmålene og ændrer den fysiske trykstørrelse.")
    if st.session_state.get("dimension_notice"):
        st.warning(st.session_state.pop("dimension_notice"))
    with st.expander("Indlæs indstillinger"):
        st.file_uploader("Vælg en JSON-fil", type="json", key="settings_upload")
        st.button("Indlæs værk", on_click=import_settings, disabled=not st.session_state.get("settings_upload"), width="stretch")
        if st.session_state.get("import_notice"):
            st.info(st.session_state["import_notice"])


config = {key: deepcopy(st.session_state[key]) for key in DEFAULTS}
if config["book_style"]:
    config = apply_book_style(config, st.session_state["book_palette"])
try:
    config = validate_config(config)
except ValueError as error:
    st.error(str(error))
    st.stop()

identity = json.dumps(config, sort_keys=True)
if st.session_state.get("bundle_identity") != identity:
    st.session_state.pop("bundle", None)
    st.session_state.pop("bundle_identity", None)

number = config["chapter"]
left, right = st.columns([5, 1])
with left:
    st.markdown('<div class="eyebrow">GENERATIV KUNST / SKABT MED PYTHON</div>', unsafe_allow_html=True)
    st.title("Fra kode til kunst.")
    st.markdown('<div class="intro">Udforsk former, find en rytme, og lad algoritmen tegne. Skab illustrationer til din bog — med koden bag hvert eneste værk.</div>', unsafe_allow_html=True)
with right:
    st.markdown(f'<div class="chapter-number">{number:02d}</div><div class="chapter-label">{"Kapitel" if number else "Fri komposition"}</div>', unsafe_allow_html=True)

art_tab, code_tab, teaching_tab, export_tab = st.tabs(["Kunstværk", "Python-kode", "Forklaring og øvelser", "Eksport"])

with art_tab:
    st.markdown(f'<div class="art-meta">{html.escape(GENERATORS[config["generator"]]["name"])} &nbsp; / &nbsp; {config["width"]} × {config["height"]} px &nbsp; / &nbsp; Seed {config["seed"]}</div>', unsafe_allow_html=True)
    with st.spinner("Algoritmen tegner dit værk …"):
        try:
            preview = preview_image(config, ENGINE_SIGNATURE)
        except (ValueError, RuntimeError, MemoryError) as error:
            st.error(f"Værket kunne ikke tegnes: {error}. Prøv en mindre størrelse eller lavere kompleksitet.")
            st.stop()
    st.image(preview, width="stretch")
    st.caption("Forhåndsvisning · hele kompositionen vises. Download i fuld opløsning under Eksport.")
    description, palette_column = st.columns([3, 1])
    with description:
        st.subheader(CHAPTERS[number][0] if number else config["preset"])
        st.write(CHAPTERS[number][3] if number else GENERATORS[config["generator"]]["concept"])
        if number and config["generator"] != CHAPTERS[number][1]:
            st.info("Du har valgt en anden generator end kapitlets anbefaling. Undervisningseksemplet følger fortsat kapitlet.")
        _, interpretation, notice = interpret_theme(config["theme"], config["theme_text"])
        if st.session_state["theme_applied"]:
            st.caption(interpretation + " " + notice + " Parametrene kan finjusteres i sidepanelet.")
        else:
            st.caption("Kompositionen bruger det valgte preset eller indlæste indstillinger. Klik Anvend tema for at anvende temafortolkningen.")
    with palette_column:
        st.markdown('<div class="section-label">Værkets palette</div>', unsafe_allow_html=True)
        st.markdown('<div class="swatches">' + ''.join(f'<span class="swatch" style="background:{color}" title="{color}"></span>' for color in config["colors"]) + '</div>', unsafe_allow_html=True)
        st.caption(config["palette"] + (" · Fælles bogstil" if config["book_style"] else ""))

code = exported_code(config, ENGINE_SIGNATURE)
with code_tab:
    st.subheader("Koden er en del af værket.")
    st.write("Den komplette fil indeholder den aktuelle generator, dens hjælpefunktioner og dine præcise indstillinger. Den kører selvstændigt uden Streamlit.")
    mode = st.radio("Kodevisning", ["Komplet kode", "Forenklet undervisningskode"], horizontal=True, label_visibility="collapsed")
    if mode == "Komplet kode":
        st.code(code, language="python", line_numbers=True)
        st.download_button("Download kunst.py", code, "kunst.py", "text/x-python", on_click="ignore", key="code_download")
    else:
        st.info("Dette eksempel forklarer grundideen og genskaber ikke det komplette værk. Fri kunst viser eksemplet om løkker og lister.")
        st.code(teaching_code(number), language="python", line_numbers=True)
        st.download_button("Download undervisning.py", teaching_code(number), "undervisning.py", "text/x-python", on_click="ignore")

with teaching_tab:
    chapter_number = number or 4
    title, _, _, explanation, exercises = CHAPTERS[chapter_number]
    st.subheader(f"{chapter_number:02d} · {title}")
    if not number:
        st.caption("Vælg et kapitel i sidepanelet for at se dets undervisningsmateriale. Her vises løkker og lister.")
    st.write(explanation)
    st.markdown("**Prøv selv**")
    for index, exercise in enumerate(exercises, start=1):
        st.write(f"{index}. {exercise}")
    st.markdown("**Figurtekst til bogen**")
    st.write(caption(config))
    sources = chapter_sources(Path(__file__).parent)
    if chapter_number in sources:
        with st.expander("Kapitlets Markdown-tekst"):
            st.markdown(sources[chapter_number]["text"])
    else:
        st.caption("Kapitelprofilen bygger på bogens kapitelliste. Der er endnu ingen tilhørende Markdown-fil i content/chapters/.")

with export_tab:
    st.subheader("Hele bogen med ét klik.")
    st.write("Generér kapitelillustrationer som JPG og den komplette Python-kode til hvert billede. "
             "Hvert kapitel bruger sit eget motiv, med plads ved kanterne til chapter-art-formatet.")
    st.selectbox("Kapitelbilledernes størrelse", list(CHAPTER_ART_SIZES), key="chapter_art_size")
    with st.expander("Filnavne til kapitelbillederne"):
        st.caption("Listen har 15 unikke kapitelnavne; kapitel 11 er med én gang. "
                   "Tilføj en ekstra linje med et unikt navn for en ekstra variant, fx chapter-11-arkitektur-for-dataudtraek-gennem-api-variant.jpg.")
        st.text_area("Ét JPG-filnavn pr. linje", value=DEFAULT_FILENAMES, key="chapter_art_filenames", height=340)
    st.caption("300 DPI · billedforhold ca. 2,234:1 · 12 % kompositionsmargin · "
               f"seriens seed: {config['seed']}. " +
               (f"Fælles bogpalette: {config['palette']}." if config["book_style"] else "Hvert kapitel bruger sin anbefalede palette."))
    jobs, chapter_art_error = [], None
    try:
        jobs = chapter_art_jobs(st.session_state["chapter_art_filenames"], seed=config["seed"],
                                size=CHAPTER_ART_SIZES[st.session_state["chapter_art_size"]],
                                book_palette=config["palette"] if config["book_style"] else None)
    except ValueError as error:
        chapter_art_error = str(error)
    chapter_art_identity = batch_identity(jobs, ENGINE_SIGNATURE) if jobs else None
    if st.session_state.get("chapter_art_identity") != chapter_art_identity:
        st.session_state.pop("chapter_art_zip", None)
        st.session_state.pop("chapter_art_identity", None)
    if chapter_art_error:
        st.warning(chapter_art_error)
    if st.button(f"Generér alle {len(jobs) or ''} kapitelbilleder + kode", key="generate_chapter_art",
                 type="primary", width="stretch", disabled=not jobs):
        chapter_progress = st.progress(0, "Forbereder alle kapitelbilleder …")
        try:
            chapter_archive = export_chapter_art(jobs, lambda value, message: chapter_progress.progress(value, text=message))
            st.session_state["chapter_art_zip"] = chapter_archive
            st.session_state["chapter_art_identity"] = chapter_art_identity
        except (ValueError, RuntimeError, MemoryError) as error:
            st.error(f"Kapitelsættet kunne ikke genereres: {error}")
        finally:
            chapter_progress.empty()
    if jobs and st.session_state.get("chapter_art_identity") == chapter_art_identity:
        st.download_button("↓  Download alle kapitelbilleder + kode · ZIP", st.session_state["chapter_art_zip"],
                           "chapter-art.zip", "application/zip", key="download_chapter_art", width="stretch", on_click="ignore")
        st.success(f"{len(jobs)} JPG-billeder og {len(jobs)} selvstændige Python-filer er klar. "
                   "ZIP-pakken indeholder også generate_all.py til at genskabe hele serien.")
    st.divider()
    st.subheader("Fra værksted til bogside.")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Pixelmål", f"{config['width']} × {config['height']}")
    col_b.metric("Trykstørrelse", f"{pixels_to_cm(config['width'], config['dpi']):.1f} × {pixels_to_cm(config['height'], config['dpi']):.1f} cm")
    col_c.metric("Opløsning", f"{config['dpi']} DPI")
    st.write("Klargør billedfilerne i fuld opløsning. ZIP-pakken indeholder også den selvstændige Python-kode, indstillinger, undervisningseksempel og figurtekst.")
    if config["generator"] == "fractal":
        st.caption("Fraktaler eksporteres som PNG og PDF med rastergrafik. SVG er tilgængeligt for de øvrige generatorer.")
    else:
        st.caption("PNG har de valgte pixelmål. SVG og PDF indeholder ægte vektorformer og linjer.")
    if st.button("Klargør eksport i fuld opløsning", type="primary", width="stretch"):
        progress = st.progress(0, "Forbereder eksport …")
        try:
            st.session_state["bundle"] = export_bundle(config, lambda value, message: progress.progress(value, text=message))
            st.session_state["bundle_identity"] = identity
        except (ValueError, RuntimeError, MemoryError) as error:
            st.error(f"Eksporten kunne ikke gennemføres: {error}")
        finally:
            progress.empty()
    if st.session_state.get("bundle_identity") == identity:
        files, archive = st.session_state["bundle"]
        st.download_button("↓  Download hele værket · ZIP", archive, "python-atelier.zip", "application/zip", type="primary", width="stretch", on_click="ignore")
        columns = st.columns(3)
        for index, fmt in enumerate(["png", "pdf", "svg"]):
            name = f"kunst.{fmt}"
            if name in files:
                columns[index].download_button(f"Download {fmt.upper()}", files[name], name,
                                               {"png": "image/png", "pdf": "application/pdf", "svg": "image/svg+xml"}[fmt], width="stretch", on_click="ignore")
        st.success("Filerne er klar med det viste seed og de aktuelle indstillinger.")
    st.divider()
    col_a, col_b, col_c = st.columns(3)
    col_a.download_button("Python-kode", code, "kunst.py", "text/x-python", key="export_code", on_click="ignore", width="stretch")
    col_b.download_button("Indstillinger · JSON", settings_json(config), "indstillinger.json", "application/json", on_click="ignore", width="stretch")
    col_c.download_button("Figurtekst · TXT", caption(config), "figurtekst.txt", "text/plain", on_click="ignore", width="stretch")

st.markdown('<div class="footer">PYTHON ATELIER &nbsp; / &nbsp; Algoritmer, der kan læses. Kunst, der kan genskabes.</div>', unsafe_allow_html=True)
