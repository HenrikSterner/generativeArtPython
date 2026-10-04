"""Kontrollér den kørende app i en rigtig browser og gem skærmbilleder."""

import io
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier.catalog import preset_config
from atelier.exports import settings_json


def main():
    folder = Path("artifacts").resolve()
    folder.mkdir(exist_ok=True)
    config = preset_config("tree", "Koralrev")
    config.update(chapter=6, width=643, height=419, seed=789)
    imported = folder / "browser-settings.json"
    imported.write_text(settings_json(config), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_role("heading", name="Fra kode til kunst.").wait_for()
        page.locator('[data-testid="stImage"] img').wait_for()
        page.screenshot(path=str(folder / "app-desktop.png"), full_page=True)

        page.get_by_text("Indlæs indstillinger", exact=True).click()
        page.get_by_test_id("stFileUploader").locator('input[type="file"]').set_input_files(imported)
        page.get_by_role("button", name="Indlæs værk", exact=True).click()
        page.get_by_text("Indstillingerne er indlæst, inklusive seed og pixelmål.", exact=True).wait_for()
        page.get_by_text("643 × 419 px", exact=False).wait_for()
        page.get_by_role("tab", name="Eksport", exact=True).click()
        page.get_by_role("button", name="Klargør eksport i fuld opløsning").click()
        download_button = page.get_by_role("button", name="Download hele værket", exact=False)
        download_button.wait_for(timeout=60000)
        with page.expect_download() as download_event:
            download_button.click()
        destination = folder / "browser-export.zip"
        download_event.value.save_as(destination)
        with zipfile.ZipFile(destination) as archive:
            exported = json.loads(archive.read("indstillinger.json"))["settings"]
            assert exported["seed"] == 789
            assert exported["chapter"] == 6
            assert Image.open(io.BytesIO(archive.read("kunst.png"))).size == (643, 419)
        page.screenshot(path=str(folder / "app-export.png"), full_page=True)
        page.get_by_role("button", name="Generér alle 15 kapitelbilleder + kode", exact=True).click()
        batch_button = page.get_by_role("button", name="Download alle kapitelbilleder + kode", exact=False)
        batch_button.wait_for(timeout=60000)
        with page.expect_download() as chapter_download:
            batch_button.click()
        batch_path = folder / "browser-chapter-art.zip"
        chapter_download.value.save_as(batch_path)
        with zipfile.ZipFile(batch_path) as archive:
            jpgs = [name for name in archive.namelist() if name.endswith(".jpg")]
            assert len(jpgs) == 15
            assert len([name for name in archive.namelist() if name.startswith("code/")]) == 15
            for name in jpgs:
                artwork = Image.open(io.BytesIO(archive.read(name)))
                assert artwork.size == (2480, 1110)
                assert artwork.info["dpi"] == (300, 300)
        page.screenshot(path=str(folder / "app-chapter-art.png"), full_page=True)
        page.get_by_role("tab", name="Kunstværk", exact=True).click()
        page.get_by_test_id("stSidebar").evaluate("element => element.scrollTop = 0")
        page.screenshot(path=str(folder / "app-recursion.png"), full_page=True)
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile = mobile_context.new_page()
        mobile.goto("http://127.0.0.1:8501", wait_until="networkidle")
        mobile.get_by_role("heading", name="Fra kode til kunst.").wait_for()
        mobile.locator('[data-testid="stImage"] img').wait_for()
        mobile.screenshot(path=str(folder / "app-mobile.png"), full_page=True)
        assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors, errors
        print("Browser OK: JSON-import, enkeltværk og alle 15 kapitel-JPG'er med kode, præcise pixelmål og ingen JavaScript-fejl.")
        browser.close()


if __name__ == "__main__":
    main()
