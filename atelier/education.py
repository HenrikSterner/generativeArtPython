"""Kapitelprofiler og små, selvstændigt kørbare undervisningseksempler."""

from pathlib import Path
from textwrap import dedent

from atelier.catalog import preset_config


CHAPTERS = {
    1: ("Dit første program", "geometry", "Formstudier", "Tre tegneinstruktioner bliver til en komposition. Rækkefølgen bestemmer, hvilke former der ligger øverst.",
        ["Skift farven på én cirkel.", "Tilføj en fjerde form med en ny tegneinstruktion.", "Lav en afbalanceret komposition med kun fem instruktioner."]),
    2: ("Variabler og deres datatyper", "geometry", "Bauhaus", "Tal styrer position og størrelse, tekstværdier vælger farver, og en boolesk værdi bestemmer udfyldning.",
        ["Ændr radius og beskriv effekten.", "Opret variabler for både x- og y-position.", "Brug en boolesk variabel til at skifte mellem omrids og udfyldning."]),
    3: ("Forgreninger: betinget udførelse", "geometry", "Formstudier", "Betingelser vælger mellem figurer. I det komplette værk bestemmer række og kolonne, hvilken gren af koden der køres.",
        ["Ændr betingelsen, så en anden figur vælges.", "Tilføj en elif-gren med en trekant.", "Lad figurens farve afhænge af en anden betingelse end dens form."]),
    4: ("Løkker og lister", "phyllotaxis", "Solsikke", "En løkke placerer prikker med den gyldne vinkel. En liste af farver gentages med modulo-operatoren.",
        ["Ændr antallet af prikker.", "Lav en liste med dine egne farver.", "Sammenlign spiraler ved 137,5 og 140 grader og forklar forskellen."]),
    5: ("Funktioner", "truchet", "Vævet", "En genbrugelig funktion tegner et motiv. Argumenter bestemmer placering, størrelse og farve i den samlede komposition.",
        ["Kald motivfunktionen på en ny position.", "Tilføj et argument for farven.", "Sammensæt en større figur af flere kald til din funktion."]),
    6: ("Rekursion", "tree", "Herbarium", "Hver gren kalder samme funktion to gange med en kortere længde. Stopbetingelsen begrænser rekursionsdybden.",
        ["Ændr rekursionsdybden fra 4 til 6.", "Giv venstre og højre gren forskellige længder.", "Udled antallet af grene som funktion af dybden og kontrollér det i kode."]),
    7: ("Objektorienteret programmering", "particles", "Koreografi", "Hver partikel er et objekt med position, hastighed og farve. Metoder opdaterer objektets tilstand og efterlader spor.",
        ["Tilføj en partikel med en anden farve.", "Giv klassen et radius-attribut.", "Lav en metode, der får en partikel til at dreje uden at ændre farten."]),
    8: ("OOP og biblioteker i praksis", "particles", "Sammenhæng", "En sværm organiserer partikelobjekter. NumPy beregner fælles egenskaber, og Matplotlib omsætter sporene til linjer.",
        ["Find sværmens gennemsnitlige position med NumPy.", "Lad partikler reagere på et fælles centrum.", "Adskil simulering og tegning, så samme data kan visualiseres på to måder."]),
    9: ("Regulære udtryk", "regex", "Ordvæv", "Regulære udtryk finder ord eller tal i en lokal tekst. Fundets længde og tegnværdier bliver til et vævet mønster.",
        ["Find alle tal i eksempelteksten.", "Find ord med mindst fem bogstaver.", "Brug navngivne grupper til at omsætte datoer til farver og positioner."]),
    10: ("Arkitektur for brugerhåndtering", "network", "Roller og relationer", "Et lokalt datasæt forbinder syntetiske brugere med roller. Dataudtræk og tegning har hver deres ansvar.",
         ["Tilføj en ny bruger med en eksisterende rolle.", "Adskil rollegruppering fra tegnefunktionen.", "Indfør en ny rolle uden at ændre den generelle netværkstegner."]),
    11: ("Arkitektur for dataudtræk gennem API", "network", "Datastrømme", "Et lokalt API-lignende svar indeholder sider med poster. Strukturen omsættes til spor fra kilde gennem sider til grupperede værdier.",
         ["Tæl posterne på hver side.", "Skriv en funktion, der samler alle sider til én liste.", "Håndtér en tom side og en post med manglende felter i et separat datalag."]),
    12: ("Maskinlæring", "clusters", "Øer af data", "K-means skifter mellem nærmeste centrum og nye gennemsnit. De beregnede klynger bestemmer punkternes farver.",
         ["Skift antallet af klynger.", "Sammenlign to seeds og deres slutcentre.", "Mål summen af kvadrerede afstande og undersøg dens udvikling gennem iterationerne."]),
    13: ("Webscraping", "html", "Dokumenttræ", "HTMLParser læser et lokalt HTML-dokument. Elementernes dybde og forældrerelationer bliver til et organisk netværk.",
         ["Tilføj et p-element i HTML-eksemplet.", "Udtræk kun bestemte tags.", "Byg en datastruktur med både forælder, tag og tekst før visualiseringen."]),
    14: ("Test i Python", "geometry", "Årringe", "Et symmetrisk motiv gør geometriske egenskaber konkrete. Tests kontrollerer symmetri, reproducerbar tilfældighed og eksporterede pixelmål.",
         ["Kør en assertion, der kontrollerer antallet af punkter.", "Test, at samme seed giver samme koordinater.", "Åbn et gemt billede og kontrollér dets faktiske pixelmål."]),
    15: ("Samarbejde gennem GitHub", "network", "Forgrening og merge", "Et lokalt datasæt af commits, forældre og grene danner spor, som deler sig og mødes igen ved merges.",
         ["Tilføj et commit med én forælder.", "Tilføj et merge-commit med to forældre.", "Flyt historik og tegnelogik til separate filer, der kan udvikles uafhængigt."]),
}


EXAMPLES = {
    1: '''
ax.add_patch(Circle((-0.45, 0.1), 0.4, color="#193e52"))
ax.add_patch(Circle((0.35, 0.1), 0.3, color="#d5ac67"))
ax.plot([-0.65, 0.65], [-0.5, -0.5], color="#b96645", linewidth=4)
''',
    2: '''
radius = 0.5                 # float: størrelsen på formen
farve = "#387782"            # str: farven
antal = 3                   # int: antal ringe
udfyldt = False             # bool: om formen er massiv
ax.add_patch(Circle((0, 0), radius, color=farve, fill=udfyldt, linewidth=antal))
''',
    3: '''
temperatur = 18
if temperatur < 10:
    ax.add_patch(Circle((0, 0), 0.5, color="#193e52"))
elif temperatur < 25:
    ax.add_patch(Polygon([(-0.5, -0.4), (0.5, -0.4), (0, 0.5)], color="#d5ac67"))
else:
    ax.add_patch(Circle((0, 0), 0.7, color="#b96645"))
''',
    4: '''
farver = ["#193e52", "#387782", "#d5ac67"]
for indeks in range(400):
    radius = 0.9 * math.sqrt(indeks / 400)
    vinkel = indeks * math.pi * (3 - math.sqrt(5))
    x, y = radius * math.cos(vinkel), radius * math.sin(vinkel)
    ax.plot(x, y, "o", color=farver[indeks % len(farver)], markersize=3)
''',
    5: '''
def motiv(x, y, radius, farve):
    ax.add_patch(Circle((x, y), radius, fill=False, color=farve, linewidth=3))
    ax.add_patch(Circle((x, y), radius / 3, color=farve))

for x in [-0.6, 0, 0.6]:
    motiv(x, 0, 0.24, "#387782")
''',
    6: '''
def gren(x, y, vinkel, længde, dybde):
    if dybde == 0:           # Stopbetingelsen er nødvendig.
        return
    slut_x = x + math.cos(vinkel) * længde
    slut_y = y + math.sin(vinkel) * længde
    ax.plot([x, slut_x], [y, slut_y], color="#387782", linewidth=dybde / 2)
    for drejning in [-0.45, 0.45]:
        gren(slut_x, slut_y, vinkel + drejning, længde * 0.7, dybde - 1)

gren(0, -0.8, math.pi / 2, 0.5, 7)
''',
    7: '''
class Partikel:
    def __init__(self, x, y, farve):
        self.x, self.y, self.farve = x, y, farve

    def flyt(self):
        self.x += 0.03
        self.y += math.sin(self.x * 4) * 0.025

    def tegn(self):
        ax.plot(self.x, self.y, ".", color=self.farve)

partikler = [Partikel(-0.9, y, "#387782") for y in [-0.4, 0, 0.4]]
for trin in range(55):
    for partikel in partikler:
        partikel.flyt()
        partikel.tegn()
''',
    8: '''
class Sværm:
    def __init__(self, antal, seed):
        self.positioner = np.random.default_rng(seed).uniform(-0.8, 0.8, (antal, 2))

    def bevæg(self):
        centrum = self.positioner.mean(axis=0)
        self.positioner += (centrum - self.positioner) * 0.04

sværm = Sværm(50, 42)
for trin in range(35):
    ax.scatter(*sværm.positioner.T, s=2, c="#387782", alpha=0.3)
    sværm.bevæg()
''',
    9: '''
import re

tekst = "Blade 12, blomster 34, grene 56 og frø 78"
fund = re.findall(r"\\d+", tekst)
for række, tal in enumerate(fund):
    for kolonne in range(int(tal) // 3):
        ax.plot(-0.85 + kolonne * 0.065, -0.6 + række * 0.4,
                "|", markersize=12, color="#b96645")
''',
    10: '''
brugere = [{"navn": "Ada", "rolle": "forfatter"},
           {"navn": "Bo", "rolle": "læser"},
           {"navn": "Clara", "rolle": "læser"}]

def gruppér(data):
    grupper = {}
    for bruger in data:
        grupper.setdefault(bruger["rolle"], []).append(bruger["navn"])
    return grupper

for række, (rolle, navne) in enumerate(gruppér(brugere).items()):
    for kolonne, navn in enumerate(navne):
        ax.plot([-0.7, 0.2 + kolonne * 0.4], [række - 0.5, række - 0.4],
                "o-", color="#387782")
''',
    11: '''
svar = {"pages": [{"items": [{"værdi": 2}, {"værdi": 5}]},
                  {"items": [{"værdi": 3}, {"værdi": 7}]}]}

def udtræk(svar):
    return [post["værdi"] for side in svar["pages"] for post in side["items"]]

for indeks, værdi in enumerate(udtræk(svar)):
    y = -0.6 + indeks * 0.4
    ax.plot([-0.8, 0, 0.8], [0, y, y / 2], color="#387782", linewidth=værdi)
''',
    12: '''
rng = np.random.default_rng(42)
punkter = np.concatenate([rng.normal(centrum, 0.18, (80, 2))
                         for centrum in [(-0.45, -0.3), (0.45, 0.3)]])
centre = punkter[[0, -1]].copy()
for trin in range(15):
    afstande = ((punkter[:, None] - centre) ** 2).sum(axis=2)
    grupper = afstande.argmin(axis=1)
    for gruppe in range(2):
        if np.any(grupper == gruppe):
            centre[gruppe] = punkter[grupper == gruppe].mean(axis=0)
grupper = ((punkter[:, None] - centre) ** 2).sum(axis=2).argmin(axis=1)
ax.scatter(*punkter.T, c=np.array(["#387782", "#d5ac67"])[grupper], s=12)
''',
    13: '''
from html.parser import HTMLParser

class Udtrækker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

parser = Udtrækker()
parser.feed("<main><h1>Kunst</h1><p>Python</p><p>Mønstre</p></main>")
for indeks, tag in enumerate(parser.tags):
    ax.add_patch(Circle((-0.6 + indeks * 0.4, 0), len(tag) * 0.05,
                        color="#387782", fill=False, linewidth=3))
''',
    14: '''
from io import BytesIO
from PIL import Image

def punkter(seed):
    venstre = np.random.default_rng(seed).uniform(-0.8, -0.1, (20, 2))
    højre = venstre * [-1, 1]
    return np.vstack([venstre, højre])

data = punkter(42)
assert len(data) == 40
assert np.array_equal(data, punkter(42))
assert np.allclose(data[:20, 0], -data[20:, 0])
ax.scatter(*data.T, c="#387782")
buffer = BytesIO()
fig.savefig(buffer, format="png", dpi=100)
assert Image.open(buffer).size == (600, 600)
''',
    15: '''
historik = [{"id": 0, "forældre": [], "spor": 0},
            {"id": 1, "forældre": [0], "spor": 1},
            {"id": 2, "forældre": [0], "spor": -1},
            {"id": 3, "forældre": [1, 2], "spor": 0}]
positioner = {post["id"]: (-0.8 + post["id"] * 0.5, post["spor"] * 0.4)
              for post in historik}
for post in historik:
    x, y = positioner[post["id"]]
    for forælder in post["forældre"]:
        px, py = positioner[forælder]
        ax.plot([px, x], [py, y], "o-", color="#387782", linewidth=2)
''',
}


def chapter_config(number):
    _, generator, preset, _, _ = CHAPTERS[number]
    config = preset_config(generator, preset)
    config["chapter"] = number
    if number == 1:
        config.update(density=5, complexity=2)
    if number == 14:
        config.update(variation=0.0, symmetry=8)
    return config


def teaching_code(number):
    number = number or 4
    header = f'''# {number:02d} — {CHAPTERS[number][0]}
# Forenklet undervisningseksempel. Genskaber ikke det komplette kunstværk.
# Installer: python -m pip install numpy matplotlib pillow
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon

fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
fig.patch.set_facecolor("#f5f1e7")
ax.set(xlim=(-1, 1), ylim=(-1, 1), aspect="equal")
ax.set_axis_off()
'''
    return header + dedent(EXAMPLES[number]) + '\nfig.savefig("undervisning.png", dpi=100, facecolor=fig.get_facecolor())\nplt.close(fig)\n'


def chapter_sources(root):
    """Find kapitler uden at kræve at bogen er installeret sammen med appen."""
    folder = Path(root) / "content" / "chapters"
    sources = {}
    for number in CHAPTERS:
        files = sorted(folder.glob(f"{number:02d}-*.md")) if folder.is_dir() else []
        if files:
            text = files[0].read_text(encoding="utf-8-sig")
            headings = [line.lstrip("# ") for line in text.splitlines() if line.startswith("#")]
            sources[number] = {"path": str(files[0]), "headings": headings, "text": text}
    return sources


def caption(config):
    number = config["chapter"]
    title = CHAPTERS[number][0] if number else "Fri algoritmisk kunst"
    explanation = CHAPTERS[number][3] if number else "En komposition skabt med en reproducerbar Python-algoritme."
    theme = config["theme_text"].strip() or config["theme"]
    return (f"{title}. {explanation} Tema: {theme}. "
            f"Seed: {config['seed']}. {config['width']} × {config['height']} pixels.")
