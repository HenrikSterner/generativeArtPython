from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_chapter_theme_generator_and_dimensions():
    app = AppTest.from_file(APP, default_timeout=45).run()
    assert not app.exception
    app.selectbox(key="chapter").select(6).run()
    assert not app.exception
    assert app.session_state["generator"] == "tree"
    app.text_area(key="theme_text").set_value("rekursion som et koralrev").run()
    assert not app.exception
    assert app.session_state["complexity"] == 9
    assert app.session_state["generator"] == "tree"
    app.checkbox(key="lock_ratio").check().run()
    app.number_input(key="width").set_value(800).run()
    assert app.session_state["height"] == 450
    app.selectbox(key="generator").select("fractal").run()
    app.selectbox(key="preset").select("Julia").run()
    assert not app.exception
    assert app.session_state["mode"] == "julia"
    # Skift væk og tilbage til widgets, der har været skjult.
    app.selectbox(key="generator").select("geometry").run()
    assert not app.exception
    assert app.slider(key="symmetry").value == 6


def test_export_invalidation_and_print_controls():
    app = AppTest.from_file(APP, default_timeout=45).run()
    app.number_input(key="width").set_value(360).run()
    app.number_input(key="height").set_value(240).run()
    seed = app.session_state["seed"]
    next(button for button in app.button if button.label == "Klargør eksport i fuld opløsning").click().run()
    assert not app.exception
    assert app.session_state["bundle_identity"]
    assert app.session_state["seed"] == seed
    app.number_input(key="width").set_value(361).run()
    assert "bundle" not in app.session_state
    app.number_input(key="cm_width").set_value(21.0).run()
    assert app.session_state["width"] == 2480
    app.number_input(key="dpi").set_value(150).run()
    assert app.session_state["width"] == 2480
    assert abs(app.session_state["cm_width"] - 41.995) < 0.01
    assert not app.exception


def test_all_chapters_in_one_session():
    app = AppTest.from_file(APP, default_timeout=45).run()
    for number in range(1, 16):
        app.selectbox(key="chapter").select(number).run()
        assert not app.exception, f"Kapitel {number}"
    app.toggle(key="book_style").set_value(True).run()
    assert not app.exception
    app.selectbox(key="book_palette").select("Sort-hvid").run()
    assert not app.exception


def test_generate_all_chapters_and_invalidate_changed_batch():
    import io
    import zipfile
    from PIL import Image

    app = AppTest.from_file(APP, default_timeout=60).run()
    original_seed = app.session_state["seed"]
    app.button(key="generate_chapter_art").click().run()
    assert not app.exception
    with zipfile.ZipFile(io.BytesIO(app.session_state["chapter_art_zip"])) as archive:
        pictures = [name for name in archive.namelist() if name.endswith(".jpg")]
        assert len(pictures) == 15
        assert all(Image.open(io.BytesIO(archive.read(name))).size == (2480, 1110) for name in pictures)
    assert app.session_state["seed"] == original_seed
    # En ændring af det enkelte billede påvirker ikke den separate serie.
    app.number_input(key="width").set_value(801).run()
    assert "chapter_art_zip" in app.session_state
    app.selectbox(key="chapter_art_size").select("3000 × 1343 px").run()
    assert "chapter_art_zip" not in app.session_state
    app.text_area(key="chapter_art_filenames").set_value("forkert.jpg").run()
    assert app.button(key="generate_chapter_art").disabled
    assert not app.exception
