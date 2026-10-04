"""Kuraterede paletter, generatorpresets og lokal fortolkning af temaer."""

from copy import deepcopy

from atelier.core import DEFAULTS, validate_config


PALETTES = {
    "Hav og guld": {"colors": ["#193e52", "#387782", "#86a7a0", "#d5ac67", "#b96645"], "background": "#f5f1e7"},
    "Nordisk": {"colors": ["#324c50", "#6b8272", "#a5b3a0", "#c8a88e", "#a4624b"], "background": "#f3f0e8"},
    "Jordfarver": {"colors": ["#6e4339", "#ad5e43", "#cb945e", "#8e956b", "#384e43"], "background": "#f5ede0"},
    "Kosmos": {"colors": ["#d6b86f", "#eee0bb", "#7a9eb4", "#46637e", "#bd7962"], "background": "#101e30"},
    "Legende": {"colors": ["#e36551", "#eab84a", "#2a8e96", "#64549a", "#d67fa0"], "background": "#fff6e7"},
    "Monokrom": {"colors": ["#163844", "#356070", "#60818b", "#849da3", "#b3c5c8"], "background": "#edf1ee"},
    "Sort-hvid": {"colors": ["#111111", "#333333", "#555555", "#777777", "#999999"], "background": "#ffffff"},
}

GENERATORS = {
    "geometry": {"name": "Geometriske mønstre", "concept": "Gentagelse · betingelser · symmetri", "presets": {
        "Formstudier": {"density": 42, "complexity": 4, "palette": "Jordfarver"},
        "Årringe": {"mode": "rings", "density": 60, "complexity": 8, "palette": "Nordisk"},
        "Bauhaus": {"density": 30, "symmetry": 3, "palette": "Legende"}}},
    "phyllotaxis": {"name": "Phyllotaxis", "concept": "Løkker · gylden vinkel · koordinater", "presets": {
        "Solsikke": {"density": 62, "palette": "Jordfarver", "complexity": 5},
        "Stjernestøv": {"density": 95, "mode": "orbit", "palette": "Kosmos"},
        "Frøstand": {"density": 30, "complexity": 3, "palette": "Nordisk"}}},
    "flow": {"name": "Flow fields", "concept": "Vektorer · funktioner · bevægelse", "presets": {
        "Tidevand": {"density": 55, "complexity": 6, "palette": "Hav og guld", "variation": 0.35},
        "Strømhvirvel": {"density": 75, "mode": "vortex", "palette": "Kosmos", "variation": 0.55},
        "Silke": {"density": 35, "mode": "vertical", "complexity": 3, "palette": "Jordfarver"}}},
    "tree": {"name": "Rekursive træer", "concept": "Rekursion · stopbetingelse · forgrening", "presets": {
        "Herbarium": {"complexity": 8, "variation": 0.32, "palette": "Nordisk"},
        "Koralrev": {"complexity": 9, "variation": 0.72, "palette": "Jordfarver"},
        "Skovbryn": {"complexity": 7, "density": 80, "mode": "forest", "palette": "Monokrom"}}},
    "fractal": {"name": "Mandelbrot og Julia", "concept": "Komplekse tal · iteration · flugttid", "presets": {
        "Mandelbrot": {"complexity": 6, "palette": "Kosmos"},
        "Julia": {"complexity": 7, "mode": "julia", "palette": "Hav og guld"},
        "Kystlinje": {"complexity": 9, "mode": "detail", "palette": "Jordfarver"}}},
    "truchet": {"name": "Truchet-fliser", "concept": "Lister · tilfældighed · mønstre", "presets": {
        "Vævet": {"density": 42, "complexity": 6, "palette": "Hav og guld"},
        "Labyrint": {"density": 80, "complexity": 2, "palette": "Sort-hvid"},
        "Bånd": {"density": 20, "complexity": 10, "palette": "Legende"}}},
    "particles": {"name": "Partikelsværme", "concept": "Klasser · objekter · NumPy", "presets": {
        "Koreografi": {"density": 40, "complexity": 6, "palette": "Nordisk"},
        "Sammenhæng": {"density": 70, "complexity": 9, "palette": "Kosmos", "variation": 0.7},
        "Kredsløb": {"density": 20, "complexity": 4, "palette": "Legende"}}},
    "regex": {"name": "Tekstvævning", "concept": "Regulære udtryk · tekst · sekvenser", "presets": {
        "Ordvæv": {"density": 45, "palette": "Jordfarver"},
        "Talrytmer": {"density": 65, "mode": "digits", "palette": "Monokrom"},
        "Manuskript": {"density": 30, "palette": "Sort-hvid", "stroke": 1.4}}},
    "network": {"name": "Netværk og strømme", "concept": "Arkitektur · relationer · datastrukturer", "presets": {
        "Roller og relationer": {"mode": "users", "palette": "Nordisk"},
        "Datastrømme": {"mode": "api", "palette": "Hav og guld"},
        "Forgrening og merge": {"mode": "git", "palette": "Kosmos"}}},
    "clusters": {"name": "Lærende klynger", "concept": "K-means · afstande · gennemsnit", "presets": {
        "Øer af data": {"density": 70, "complexity": 5, "palette": "Hav og guld", "variation": 0.32},
        "Konstellationer": {"density": 45, "complexity": 7, "palette": "Kosmos", "variation": 0.55},
        "Familier": {"density": 30, "complexity": 3, "palette": "Legende", "variation": 0.2}}},
    "html": {"name": "Dokumentets grene", "concept": "HTML · udtræk · hierarkier", "presets": {
        "Dokumenttræ": {"palette": "Nordisk", "stroke": 1.2},
        "Hypertekst": {"palette": "Kosmos", "stroke": 1.8},
        "Papirspor": {"palette": "Jordfarver", "stroke": 0.6}}},
}

THEMES = {
    "Nordisk minimalisme": {"words": ["nordisk", "minimal", "rolig", "enkel"], "generator": "geometry", "palette": "Nordisk", "density": 25, "complexity": 3, "variation": 0.12, "margin": 0.16, "description": "Få former, afdæmpede farver, lav variation og god plads omkring motivet."},
    "Botaniske strukturer": {"words": ["botan", "blad", "skov", "plante", "blomst", "natur", "grøn"], "generator": "tree", "palette": "Nordisk", "complexity": 8, "variation": 0.4, "description": "Organiske forgreninger, grønne jordfarver og kontrolleret asymmetri."},
    "Havstrømme": {"words": ["hav", "bølge", "strøm", "vand", "ocean"], "generator": "flow", "palette": "Hav og guld", "density": 65, "variation": 0.42, "description": "Flydende rytmer, blågrønne farver og gyldne detaljer."},
    "Kosmiske landskaber": {"words": ["kosmi", "stjerne", "rum", "galakse", "planet"], "generator": "phyllotaxis", "palette": "Kosmos", "density": 80, "complexity": 7, "variation": 0.6, "description": "Mørk baggrund, fine lysende detaljer og tætte strukturer."},
    "Geometrisk arkitektur": {"words": ["geometri", "arkitektur", "bygning", "symmetri"], "generator": "geometry", "palette": "Jordfarver", "symmetry": 8, "density": 45, "variation": 0.08, "description": "Regelmæssige moduler, stærk symmetri og varme materialefarver."},
    "Digitale netværk": {"words": ["netværk", "digital", "forbind", "system", "maskine"], "generator": "network", "palette": "Monokrom", "density": 65, "stroke": 1.3, "description": "Forbundne strukturer med tydelige spor og kølige farver."},
    "Orden og kaos": {"words": ["kaos", "orden", "tilfæld", "vild"], "generator": "truchet", "palette": "Legende", "density": 75, "variation": 0.9, "complexity": 8, "description": "Mange gentagelser med høj variation og markante farveskift."},
    "Koralrev": {"words": ["koral", "rev"], "generator": "tree", "palette": "Jordfarver", "complexity": 9, "variation": 0.72, "description": "Tæt forgrening, bred spredning og varme koralfarver."},
    "Tekstilkunst": {"words": ["tekstil", "væv", "stof", "silke", "tråd"], "generator": "regex", "palette": "Jordfarver", "density": 75, "stroke": 1.3, "variation": 0.24, "description": "Tætte bånd, rytmiske gentagelser og varme tekstilfarver."},
    "Øer af datapunkter": {"words": ["øer", "data", "klynge", "læring"], "generator": "clusters", "palette": "Hav og guld", "density": 70, "complexity": 5, "variation": 0.28, "description": "Grupper af små former, organiske øer og blågrønne farver."},
}


def preset_config(generator, preset):
    config = deepcopy(DEFAULTS)
    choices = GENERATORS[generator]["presets"]
    config.update(choices[preset])
    config.update(generator=generator, preset=preset)
    config.update(deepcopy(PALETTES[config["palette"]]))
    return config


def interpret_theme(name, text=""):
    """Forklar præcist hvilke lokale nøgleord der blev genkendt."""
    selected = name if name in THEMES else "Nordisk minimalisme"
    hits = []
    text_lower = text.casefold()
    if text.strip():
        for theme, values in THEMES.items():
            words = [word for word in values["words"] if word in text_lower]
            if words:
                hits.append((len(words), theme, words))
        if hits:
            _, selected, words = max(hits, key=lambda item: item[0])
            notice = f"Lokal nøgleordsfortolkning: {', '.join(words)}. Resten af friteksten fortolkes ikke automatisk."
        else:
            notice = f"Ingen kendte temaord fundet. Bruger det valgte tema: {selected}."
    else:
        notice = "Temaet bruger et kurateret sæt visuelle indstillinger."
    values = THEMES[selected]
    patch = {key: value for key, value in values.items() if key in DEFAULTS}
    patch.update(deepcopy(PALETTES[values["palette"]]))
    return patch, values["description"], notice


def apply_book_style(config, palette):
    config = deepcopy(config)
    config.update(palette=palette, **deepcopy(PALETTES[palette]))
    config.update(margin=0.12, stroke=1.0, book_style=True)
    return config


def validate_catalog_config(config):
    config = validate_config(config)
    if config["palette"] not in PALETTES:
        raise ValueError("Ukendt paletnavn i indstillingerne.")
    if config["theme"] not in THEMES:
        raise ValueError("Ukendt tema i indstillingerne.")
    if config["preset"] not in GENERATORS[config["generator"]]["presets"]:
        raise ValueError("Preset passer ikke til den valgte generator.")
    return config
