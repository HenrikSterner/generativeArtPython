# Python Atelier

En dansk Streamlit-app til at skabe generativ kunst og undervisningsillustrationer med Python. Vælg et af bogens 15 kapitler, et tema og præcise pixelmål, og download både kunstværket og den selvstændige Python-kode bag det.

## Start på Windows

Brug Python 3.12 eller nyere. Kør fra projektmappen:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Åbn den lokale adresse, som Streamlit viser, normalt http://localhost:8501. Det er ikke nødvendigt at aktivere miljøet i PowerShell.

Miljøet i dette projekt er allerede installeret med `uv`. Her kan appen startes direkte med den sidste kommando. Alternativ installation med uv:

```powershell
uv --cache-dir .uv-cache venv .venv
uv --cache-dir .uv-cache pip install --python .venv\Scripts\python.exe -r requirements.txt
```

På macOS/Linux bruges `.venv/bin/python` i stedet for `.venv\Scripts\python.exe`.

## Arbejdsgang

1. Vælg **Fri kunst** eller et kapitel. Kapitelvalget henter en anbefalet generator og et preset.
2. Vælg et tema eller skriv fx “rekursion som et koralrev”. Temaet anvendes ved ændringen eller med **Anvend tema**. Et kapitel bevarer sin generator; i fri kunst kan temaet også vælge generator.
3. Justér palette, parametre og seed. **Ny variation** vælger et nyt seed; almindelig eksport bevarer det eksisterende.
4. Angiv bredde og højde i pixels. Du kan låse billedformatet eller ombytte siderne. Trykmål i centimeter omregnes til faktiske pixelmål ved den valgte DPI. Ændring af DPI alene bevarer pixelmålene.
5. Se hele kompositionen under **Kunstværk**, den faktiske kildekode under **Python-kode** og kapitelmaterialet under **Forklaring og øvelser**.
6. Vælg **Klargør eksport i fuld opløsning** under **Eksport**. Download enkelte filer eller hele pakken. Når indstillinger ændres, fjernes tidligere eksportfiler fra brugerfladen, indtil det nye værk klargøres.

Temaer bruger lokale nøgleordsregler, ikke en sprogmodel. Appen viser genkendte ord og oplyser, når øvrig fritekst ikke fortolkes. Ukendte temaord bruger det valgte tema som udgangspunkt. Et nyt preset erstatter de visuelle indstillinger; temaet kan derefter anvendes igen.

**Fælles bogstil** fastlægger en delt palette, baggrund, margin og linjestørrelse på tværs af kapitler. Stilens effektive indstillinger følger med alle eksporter.

## Generér alle kapitelbilleder og deres kode

Under **Eksport → Hele bogen med ét klik** findes knappen **Generér alle 15 kapitelbilleder + kode**. Standardlisten følger de oplyste filnavne, inklusive `chapter-11-arkitektur-for-dataudtraek-gennem-api.jpg` og stavningen `chapter-13-webscrabing.jpg`. Der er 15 unikke navne; den gentagne kapitel 11-fil er med én gang.

- Standard: **2480 × 1110 pixels**, 300 DPI, cirka **2,234:1**. Alternativt **3000 × 1343 pixels**.
- JPG i kvalitet 95 uden farveundersampling og med fast baggrund.
- Hvert kapitel får sit eget anbefalede motiv og et deterministisk seed udledt fra seedet i sidepanelet.
- En kompositionsmargin på 12 % holder motivet væk fra kanterne ved minimal `fit: "cover"`-beskæring.
- Fælles bogstil bruges, hvis den er slået til. Ellers bruger kapitlerne deres anbefalede paletter.

Download derefter **alle kapitelbilleder + kode · ZIP**. Billederne ligger i pakkens rod med bogens filnavne; `code/` indeholder én selvstændig `.py`-fil med samme basisnavn pr. billede. `settings/` indeholder indstillingerne. `manifest.json` beskriver hele sættet.

Efter udpakning kan alle JPG-filer genskabes uden appen:

```powershell
python -m pip install -r requirements.txt
python generate_all.py
```

En enkelt fil fra `code/` kan også køres direkte; den gemmer automatisk en JPG med det tilhørende kapitelnavn. Samme biblioteksversioner genskaber samme JPEG-data.

Filnavnelisten kan redigeres i appen. For 16 billeder tilføjes et unikt navn til den ekstra variant, fx `chapter-11-arkitektur-for-dataudtraek-gennem-api-variant.jpg`. Kapitelnummeret vælger motivtypen, og varianten får sit eget seed. Dublerede filnavne og manglende kapitler afvises. Størrelse, seed, filnavne og fælles bogstil følger den enkelte serie; ændres de, skal serien genereres igen.

## Generatorer og kapitler

Der er 11 generatorfamilier og 33 presets:

| Generator | Idé | Anbefalede kapitler |
|---|---|---|
| Geometriske mønstre | Figurer, symmetri og betingelser | 1, 2, 3, 14 |
| Phyllotaxis | Solsikkespiraler med den gyldne vinkel | 4 |
| Flow fields | Kurver i et glat vektorfelt | Fri kunst |
| Rekursive træer | Forgrening med stopbetingelse | 6 |
| Mandelbrot og Julia | Iteration af komplekse tal | Fri kunst |
| Truchet-fliser | Buer, der forbindes på tværs af fliser | 5 |
| Partikelsværme | Objekter, bevægelse og NumPy | 7, 8 |
| Tekstvævning | Faktiske regex-fund i en lokal tekst | 9 |
| Netværk og strømme | Roller, API-lignende data og commitgrafer | 10, 11, 15 |
| Lærende klynger | Faktisk k-means-beregning | 12 |
| Dokumentets grene | Udtræk med HTMLParser | 13 |

Hvert kapitel har en profil, en forklaring, et selvstændigt undervisningseksempel, tre øvelser og en figurtekst. Undervisningskoden er forenklet og skal ikke forveksles med den komplette kode, der genskaber kunstværket.

Bogfilerne var ikke til stede ved implementeringen. Profilerne bygger derfor på den oplyste kapitelliste. Lægges Markdown-filer i `content/chapters/01-*.md` til `15-*.md`, viser appen deres tekst sammen med kapitlet. Den omskriver ikke undervisningsprofiler automatisk ud fra nye dokumenter; de vedligeholdes i `atelier/education.py`.

## Eksport

- **PNG:** Præcise pixelmål, DPI-metadata og valgfri transparens.
- **SVG/PDF:** Ægte vektorformer for alle generatorer bortset fra fraktaler.
- **Fraktaler:** PNG eller PDF med rastergrafik ved den valgte opløsning. SVG tilbydes ikke.
- **kunst.py:** Den valgte generators faktiske funktioner, hjælpefunktioner, lokale data og aktuelle indstillinger. Ingen imports fra appen og ingen Streamlit-afhængighed.
- **indstillinger.json:** Kapitel, tema, seed, alle parametre, dimensioner, farver, biblioteksversioner og tegnemotorens SHA-256.
- **figurtekst.txt** og **undervisning.py**.
- **ZIP:** Alle ovenstående relevante filer samlet.

Kør en downloadet generator i en mappe uden appen:

```powershell
python -m pip install numpy matplotlib pillow
python kunst.py --output mit-vaerk.png
python kunst.py --output mit-vaerk.pdf
```

Første kommentar i `kunst.py` angiver også den præcise installationskommando med versionsnumre fra eksporten. Brug samme versioner og platform, hvis du skal sammenligne pixels nøjagtigt. Preview bruger en mindre opløsning; kompositionen og tilfældighedsforløbet er de samme, mens rasterfraktaler samples ved previewets opløsning.

Alle eksempler er lokale og kræver ingen API-nøgle eller adgang til GitHub/websteder. Kodevisningen er til kopiering og download og udfører ikke brugerindtastet Python.

Grænser: 64–8000 pixels pr. side, højst 24 millioner pixels samlet og 72–600 DPI. Store fraktaler eller vektortegninger kan tage længere tid. Appen viser fremdrift mellem eksportformater; en igangværende individuel rendering afsluttes, før næste format starter.

## Projektstruktur

```text
app.py                 Streamlit-brugerflade og sessionstilstand
atelier/core.py        Selvstændig tegnemotor og validering
atelier/catalog.py     Presets, temaer og paletter
atelier/education.py   15 kapitelprofiler og undervisningseksempler
atelier/exports.py     Kildekode, JSON, ZIP og versionsoplysninger
atelier/batch.py       Alle kapitel-JPG'er, filnavne og samlet genskabelse
atelier/ui_state.py    Pixelmål og konvertering til trykstørrelse
tests/                 Generator-, eksport- og brugerfladetests
scripts/gallery.py     Kontaktark til visuel gennemgang
scripts/browser_check.py Browserkontrol af import og download
```

Tilføj en generator ved at implementere dens tegnefunktion, registrere den i `core.RENDERERS` og tilføje presets i `catalog.GENERATORS`. Kodeeksporten finder automatisk dens afhængigheder blandt tegnemotorens funktioner og klasser.

## Verifikation

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\gallery.py
```

Hvis miljøet er oprettet med uv, kan afhængighederne i stedet installeres med `uv --cache-dir .uv-cache pip install --python .venv\Scripts\python.exe -r requirements-dev.txt`.

Testene kontrollerer alle presets og kapitler, pixelmål i de ønskede billedformater, determinisme, JSON/ZIP, inputvalidering, vektoreksport, undervisningskode og eksportfilers uafhængighed af projektet. De eksporterede filer køres som separate processer i midlertidige mapper, og deres pixels sammenlignes med tegnemotorens output.

Ved leveringen bestod 144 tests med Python 3.14.4. Browserkontrollen bestod også: JSON-import, faktisk ZIP-download af enkeltværker og hele kapitelsættet, præcise billeddimensioner og mobilvisning uden vandret sidescroll. Alle 33 presets og 15 kapitelkompositioner er gennemgået på kontaktark, inklusive de nye JPG-bannere. Det samlede genskabelsesscript er kørt uden adgang til projektet og sammenlignet med de eksporterede JPEG-data.

Browserkontrollen forventer en app på port 8501 og Microsoft Edge installeret:

```powershell
.\.venv\Scripts\python.exe scripts\browser_check.py
```

Kontaktark, skærmbilleder og midlertidige eksportfiler gemmes under `artifacts/`, som ikke versionsstyres.

Streamlits officielle dokumentation beskriver [downloadknapper uden rerun](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button) og [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest), som bruges i løsningen.
