import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import altair as alt
import random
import streamlit_autorefresh
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components
import re

st.set_page_config(page_title="📺 Live Spielstand", layout="wide")

# Auto-Refresh alle 1 Minuten (60.000 Millisekunden)
streamlit_autorefresh.st_autorefresh(interval=60_000, key="refresh")

# 🔒 Fester Spielname – HIER ANPASSEN!
FESTER_SPIELNAME = "Vatertagsspiele 2026"

# Firebase verbinden (GECACHT - wird nur einmal ausgeführt)
@st.cache_resource
def get_firestore_client():
    """Initialisiert Firebase Client und cached die Instanz."""
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

# 🚀 NEUE FUNKTION: Spieldaten aus Firebase laden (GECACHT!)
@st.cache_data(ttl=300)  # Cache für 5 Minuten
def lade_spieldaten(spielname):
    """
    Lädt Spieldaten aus Firebase und cached sie für 5 Minuten.
    
    Args:
        spielname: Name des Spiels
        
    Returns:
        dict: Spieldaten oder None bei Fehler
    """
    spiel_doc = db.collection("spiele").document(spielname).get()
    if not spiel_doc.exists:
        return None
    return spiel_doc.to_dict()

# 🚀 NEUE FUNKTION: Punkte berechnen (GECACHT!)
@st.cache_data(ttl=300)
def berechne_punktestand(spieler_liste, runden_liste, multiplikatoren_liste):
    """
    Berechnet Punktestand, Verlauf und Bonus-Empfänger.
    Wird nur bei Änderungen neu berechnet!
    
    Args:
        spieler_liste: Liste der Spieler
        runden_liste: Liste der Runden
        multiplikatoren_liste: Multiplikatoren für Plätze
        
    Returns:
        tuple: (spieler, punkteverlauf, bonus_empfaenger_pro_runde)
    """
    # Deep copy um Original nicht zu verändern
    spieler = [sp.copy() for sp in spieler_liste]
    
    # Initialisierung
    for sp in spieler:
        sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
        sp["punkte"] = 20.0

    punkteverlauf = []
    zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}
    bonus_empfaenger_pro_runde = []

    # Startrunde hinzufügen
    for sp_name in zwischenpunkte:
        punkteverlauf.append({
            "Runde": "0: Start",
            "Spieler": sp_name,
            "Punkte": 20.0
        })

    # Runden durchgehen
    for i, runde in enumerate(runden_liste):
        letzter_spieler = min(zwischenpunkte, key=zwischenpunkte.get)
        bonus_empfaenger_pro_runde.append(letzter_spieler)

        for sp in spieler:
            einsatz = runde["einsaetze"].get(sp["name"], 0)
            platz = runde["plaetze"].get(sp["name"], 1)
            multiplikator = multiplikatoren_liste[platz - 1] if platz - 1 < len(multiplikatoren_liste) else 0
            gewinn = einsatz * multiplikator

            # Rubber-Banding
            if sp["name"] == letzter_spieler and gewinn < 0:
                gewinn = 0

            sp["einsaetze"].append(einsatz)
            sp["plaetze"].append(platz)
            sp["gewinne"].append(gewinn)
            sp["punkte"] += gewinn
            zwischenpunkte[sp["name"]] += gewinn
            
            punkteverlauf.append({
                "Runde": f"{i+1}: {runde['name']}",
                "Spieler": sp["name"],
                "Punkte": zwischenpunkte[sp["name"]]
            })

    return spieler, punkteverlauf, bonus_empfaenger_pro_runde

# 🚀 NEUE FUNKTION: Kommentare generieren (GECACHT!)
@st.cache_data(ttl=300)
def generiere_kommentar(spieler_liste, runden_liste, bonus_empfaenger_pro_runde):
    """
    Generiert Spielkommentar basierend auf aktuellem Spielstand.
    
    Returns:
        str: Formatierter Kommentar
    """
    zwischenpunkte = {sp["name"]: sp["punkte"] for sp in spieler_liste}
    
    # Letzte Runde analysieren
    letzte_runde_idx = len(runden_liste) - 1
    gewinne_letzte_runde = [
        (sp["name"], sp["gewinne"][letzte_runde_idx]) 
        for sp in spieler_liste
    ]
    
    aktueller_fuehrender = max(zwischenpunkte, key=zwischenpunkte.get)
    aktueller_letzter = min(zwischenpunkte, key=zwischenpunkte.get)
    rundensieger = max(gewinne_letzte_runde, key=lambda x: x[1])
    bonus_empfaenger = bonus_empfaenger_pro_runde[letzte_runde_idx] if letzte_runde_idx > 0 else None

    # Kommentar-Templates
    kommentare_fuehrend = [
    "🥇 **{name}** führt jetzt mit {punkte:.1f} Punkten. Niemand stoppt diesen Siegeszug!",
    "🚀 **{name}** stürmt an die Spitze! {punkte:.1f} Punkte und kein Ende in Sicht!",
    "👑 **{name}** thront über allen mit {punkte:.1f} Punkten. Ein König unter Spielern!",
    "🏆 {name} setzt sich ab mit {punkte:.1f} Punkten, eine wahre Meisterleistung!",
    "🔥 **{name}** brennt ein Punktefeuerwerk ab – {punkte:.1f} Zähler auf dem Konto!",
    "🌪️ **{name}** wirbelt durch das Feld! {punkte:.1f} Punkte und kein Halten mehr!",
    "🧨 **{name}** sprengt alle Grenzen mit {punkte:.1f} Punkten, was für ein Lauf!",
    "🦁 **{name}** zeigt Löwenmut und dominiert mit {punkte:.1f} Punkten!",
    "🧠 **{name}** spielt in einer eigenen Liga – {punkte:.1f} Punkte sprechen Bände!",
    "🏹 **{name}** trifft ins Schwarze! {punkte:.1f} Punkte und die Führung ist sicher!",
    "🛡️ **{name}** verteidigt die Spitze mit {punkte:.1f} Punkten, unaufhaltsam!",
    "🎯 **{name}** punktet präzise und führt mit {punkte:.1f} Punkten, zielstrebig zum Sieg!",
    "🏇 **{name}** galoppiert dem Feld davon, {punkte:.1f} Punkte auf dem Konto!",
    ]

    kommentare_letzter = [
    "🐢 **{name}** hinkt mit {punkte:.1f} Punkten hinterher. Vielleicht war das ein geheimer Plan?",
    "🪨 **{name}** hält das Feld stabil von hinten, {punkte:.1f} Punkte und viel Luft nach oben.",
    "🌌 **{name}** ist auf Entdeckungsreise im unteren Punktesektor ({punkte:.1f}).",
    "🕳️ **{name}** erkundet die Tiefen der Punktetabelle mit {punkte:.1f} Punkten, ganz ohne Eile.",
    "🐌 **{name}** nimmt das Rennen gelassen, {punkte:.1f} Punkte und jede Menge Potenzial!",
    "🧊 **{name}** bleibt cool am Tabellenende mit {punkte:.1f} Punkten, vielleicht kommt der große Sprung noch?",
    "🌱 **{name}** wächst langsam, aber stetig, {punkte:.1f} Punkte sind erst der Anfang.",
    "🪁 **{name}** schwebt am unteren Rand mit {punkte:.1f} Punkten, bereit für den Aufwind?",
    "🛸 **{name}** funkt aus der unteren Liga, {punkte:.1f} Punkte und eine Mission im Gange.",
    "🦥 **{name}** bewegt sich gemächlich mit {punkte:.1f} Punkten, aber unterschätze nie den Spätstarter!",
    "🧭 **{name}** sucht noch den Weg zum Punktetriumph – aktuell bei {punkte:.1f} Punkten.",
    "🎒 **{name}** sammelt Erfahrung am Tabellenende, {punkte:.1f} Punkte sind nur der Anfang.",
    "🪶 **{name}** landet sanft auf dem letzten Platz mit {punkte:.1f} Punkten, aber wer weiß, wie lange noch?",
    ]

    kommentare_rundensieger = [
    "💥 **{name}** schnappt sich diese Runde mit {gewinn:.1f} Punkten. Boom!",
    "🔥 **{name}** dominiert die Runde! {gewinn:.1f} Punkte sind kein Zufall.",
    "🎯 **{name}** trifft ins Schwarze, {gewinn:.1f} Punkte in einer Runde!",
    "⚡ **{name}** zündet den Turbo und holt {gewinn:.1f} Punkte, was für ein Move!",
    "🏹 **{name}** zielt perfekt, {gewinn:.1f} Punkte gehen direkt aufs Konto!",
    "🚀 **{name}** hebt ab und landet {gewinn:.1f} Punkte, das war galaktisch!",
    "🎉 **{name}** feiert den Rundensieg mit {gewinn:.1f} Punkten, verdient und eindrucksvoll!",
    "🧨 **{name}** lässt es krachen, {gewinn:.1f} Punkte in einem Durchgang!",
    "🏆 **{name}** holt sich den Pokal dieser Runde mit {gewinn:.1f} Punkten, stark gespielt!",
    "🕶️ **{name}** bleibt cool und punktet {gewinn:.1f}, ein echter Profi!",
    "🧠 **{name}** spielt clever und sichert sich {gewinn:.1f} Punkte, Strategie zahlt sich aus!",
    "🎲 **{name}** würfelt das Glück auf seine Seite, {gewinn:.1f} Punkte!",
    "🦾 **{name}** zeigt Stärke und holt {gewinn:.1f} Punkte, eine Maschine auf dem Spielfeld!",
    ]

    kommentare_bonus = [
    "🧲 **{name}** bekommt den Bonus – Letzter sein zahlt sich wohl doch aus!",
    "🔁 **{name}** nutzt Rubber-Banding – vielleicht klappt's ja nächstes Mal richtig!",
    "🎁 Bonuszeit für **{name}**! Manchmal ist Verlieren einfach lohnenswert.",
    "🪄 **{name}** zaubert sich den Bonus herbei – Extra-Punkte für Durchhaltevermögen!",
    "🧃 **{name}** bekommt einen Energieschub – Bonuspunkte für den Comeback-Versuch!",
    "🛠️ **{name}** rüstet nach mit Bonuspunkten – vielleicht klappt’s im nächsten Anlauf?",
    "🎈 **{name}** wird belohnt fürs Durchhalten – Bonuspunkte fliegen ein,",
    "🧸 **{name}** bekommt Trostpunkte – Bonus für den Mut, weiterzuspielen.",
    "🔋 **{name}** lädt sich neu auf – Bonuspunkte für frischen Schwung!",
    "🌀 **{name}** dreht das Momentum – Bonuspunkte könnten alles ändern.",
    "📦 **{name}** packt den Bonus aus – ein Geschenk für den Underdog.",
    "🧬 **{name}** bekommt evolutionäre Unterstützung – Bonuspunkte für den nächsten Schritt.",
    "🕹️ **{name}** aktiviert den Bonus-Modus – vielleicht ist das der Gamechanger!",
    ]

    kommentare_bonus_gewinnt = [
    "⚡ **{name}** nutzt Rubber-Banding und rasiert die Runde mit {gewinn:.1f} Punkten!",
    "👀 **{name}** kommt von hinten – mit Bonus {gewinn:.1f} Punkte! Da staunt das Feld.",
    "🧨 **{name}** startet durch! Rubber-Banding at its best: {gewinn:.1f} Punkte!",
    "🚀 **{name}** zündet den Nachbrenner und holt {gewinn:.1f} Punkte, das ist Comeback-Power!",
    "🎮 **{name}** spielt Reverse-Mode – von hinten nach vorn mit {gewinn:.1f} Punkten!",
    "🦘 **{name}** springt aus dem Schatten und kassiert {gewinn:.1f} Punkte, das nennt man Timing!",
    "🧃 **{name}** tankt Bonusenergie und liefert {gewinn:.1f} Punkte ab, das war stark!",
    "🎢 **{name}** fährt Achterbahn – ganz unten gestartet, ganz oben gelandet mit {gewinn:.1f} Punkten!",
    "🕹️ **{name}** aktiviert den Comeback-Code, {gewinn:.1f} Punkte aus dem Nichts!",
    "🪂 **{name}** landet punktgenau, {gewinn:.1f} Punkte aus der Tiefe des Feldes!",
    "🧬 **{name}** mutiert zum Rundensieger, {gewinn:.1f} Punkte durch Bonus-Evolution!",
    "🎯 **{name}** trifft aus dem Off, {gewinn:.1f} Punkte und alle schauen verdutzt!",
    "🦾 **{name}** zeigt Comeback-Qualitäten, {gewinn:.1f} Punkte und plötzlich ganz vorn!",
    ]

    # Kommentar zusammenbauen
    kommentar_text = ""
    
    if bonus_empfaenger and rundensieger[0] == bonus_empfaenger:
        kommentar_text += random.choice(kommentare_bonus_gewinnt).format(
            name=rundensieger[0], gewinn=rundensieger[1]
        ) + "\n"
    else:
        kommentar_text += random.choice(kommentare_rundensieger).format(
            name=rundensieger[0], gewinn=rundensieger[1]
        ) + "\n"

    kommentar_text += random.choice(kommentare_fuehrend).format(
        name=aktueller_fuehrender, punkte=zwischenpunkte[aktueller_fuehrender]
    ) + "\n"
    
    kommentar_text += random.choice(kommentare_letzter).format(
        name=aktueller_letzter, punkte=zwischenpunkte[aktueller_letzter]
    ) + "\n"
    
    if bonus_empfaenger:
        kommentar_text += random.choice(kommentare_bonus).format(name=bonus_empfaenger)

    return kommentar_text

# 🚀 NEUE FUNKTION: Statistiken berechnen (GECACHT!)
@st.cache_data(ttl=300)
def berechne_statistiken(spieler_liste, bonus_empfaenger_pro_runde, punkteverlauf_liste):
    """
    Berechnet alle Spielstatistiken.
    
    Returns:
        dict: Dictionary mit allen Statistiken
    """
    stats = {}
    
    # 1. Häufigster Rundensieger
    rundensieger_namen = []
    for i in range(len(spieler_liste[0]["gewinne"])):
        rundensieger = max(spieler_liste, key=lambda sp: sp["gewinne"][i])
        rundensieger_namen.append(rundensieger["name"])
    
    if rundensieger_namen:
        rundensieger_counts = pd.Series(rundensieger_namen).value_counts()
        stats["haeufigster_rundensieger"] = rundensieger_counts.idxmax()
        stats["rundensieger_anzahl"] = int(rundensieger_counts.max())
    else:
        stats["haeufigster_rundensieger"] = "–"
        stats["rundensieger_anzahl"] = 0

    # 2. Höchster Punktestand
    df_punkte_max = pd.DataFrame(punkteverlauf_liste)
    max_row = df_punkte_max.loc[df_punkte_max["Punkte"].idxmax()]
    stats["max_punkte"] = float(max_row["Punkte"])
    stats["max_punkte_spieler"] = max_row["Spieler"]
    stats["max_punkte_runde"] = max_row["Runde"]

    # 3. Häufigster Bonus-Empfänger
    bonus_daten = bonus_empfaenger_pro_runde[1:]
    if bonus_daten:
        bonus_counter = pd.Series(bonus_daten).value_counts()
        stats["haeufigster_bonus_spieler"] = bonus_counter.idxmax()
        stats["bonus_anzahl"] = int(bonus_counter.max())
    else:
        stats["haeufigster_bonus_spieler"] = "–"
        stats["bonus_anzahl"] = 0

    # 4. Risikofreudigster Spieler
    einsatz_durchschnitt = {
        sp["name"]: sum(sp["einsaetze"]) / len(sp["einsaetze"]) if sp["einsaetze"] else 0
        for sp in spieler_liste
    }
    stats["risikofreudigster_spieler"] = max(einsatz_durchschnitt, key=einsatz_durchschnitt.get)
    stats["max_durchschnitt_einsatz"] = einsatz_durchschnitt[stats["risikofreudigster_spieler"]]

    # 5. Effektivster Spieler
    effizienz = {}
    for sp in spieler_liste:
        gesamt_einsatz = sum(sp["einsaetze"])
        gesamt_gewinn = sum(sp["gewinne"])
        effizienz[sp["name"]] = gesamt_gewinn / gesamt_einsatz if gesamt_einsatz > 0 else 0
    stats["effektivster_spieler"] = max(effizienz, key=effizienz.get)
    stats["effizienz_wert"] = effizienz[stats["effektivster_spieler"]]

    # 6. Konstantester Spieler
    gewinn_durchschnitt = {
        sp["name"]: sum(sp["gewinne"]) / len(sp["gewinne"]) if sp["gewinne"] else 0
        for sp in spieler_liste
    }
    stats["konstantester_spieler"] = max(gewinn_durchschnitt, key=gewinn_durchschnitt.get)
    stats["konstanter_gewinn"] = gewinn_durchschnitt[stats["konstantester_spieler"]]

    # 7. Bonus-Effizienz
    bonus_sieger = {}
    for i, bonus_empf in enumerate(bonus_empfaenger_pro_runde[1:], start=1):
        if i < len(spieler_liste[0]["gewinne"]):
            rundensieger = max(spieler_liste, key=lambda sp: sp["gewinne"][i])
            if bonus_empf == rundensieger["name"]:
                bonus_sieger[bonus_empf] = bonus_sieger.get(bonus_empf, 0) + 1

    if bonus_sieger:
        stats["bester_bonusnutzer"] = max(bonus_sieger, key=bonus_sieger.get)
        stats["bester_bonusnutzer_anzahl"] = bonus_sieger[stats["bester_bonusnutzer"]]
    else:
        stats["bester_bonusnutzer"] = "–"
        stats["bester_bonusnutzer_anzahl"] = 0

    # 8. Spannungsindex
    punkte_liste = [sp["punkte"] for sp in spieler_liste]
    stats["spannungsindex"] = float(pd.Series(punkte_liste).std())

    return stats


# ==================== HAUPTPROGRAMM ====================

st.title("🎲 Vatertagsspiele 2026 - Spielstand (live)")

# Spiel laden (GECACHT!)
daten = lade_spieldaten(FESTER_SPIELNAME)
if not daten:
    st.error(f"Spiel '{FESTER_SPIELNAME}' nicht gefunden.")
    st.stop()

# Punkte berechnen (GECACHT!)
spieler, punkteverlauf, bonus_empfaenger_pro_runde = berechne_punktestand(
    daten["spieler"], 
    daten["runden"], 
    daten["multiplikatoren"]
)

# Kommentar generieren (GECACHT!)
@st.cache_data(ttl=300, show_spinner=False)
def generiere_kommentar_cached(spieler_liste, runden_liste, bonus_empfaenger_pro_runde):
    # Wir erzeugen einen Hash/Key basierend auf dem Punktestand der aktuellen Runde
    aktuelle_punkte = tuple(sp["punkte"] for sp in spieler_liste)
    # Der Cache nutzt den Key automatisch über die Funktionseingaben
    return generiere_kommentar(spieler_liste, runden_liste, bonus_empfaenger_pro_runde)
    
kommentar = generiere_kommentar_cached(spieler, daten["runden"], bonus_empfaenger_pro_runde)

#Sprachausgabe des Kommentars
kommentar_clean = re.sub(r"\*+", "", kommentar)

# Emojis entfernen (alles außerhalb von Standardzeichen)
kommentar_clean = re.sub(r"[^\w\s.,!?-]", "", kommentar_clean)

# . druch , ersetzen
kommentar_clean = kommentar_clean.replace(".", ",")

components.html(
    f"""
    <script>
        // Kommentar, der gesprochen werden soll
        const text = {json.dumps(kommentar_clean)};

        // Neue SpeechSynthesisUtterance erstellen
        const msg = new SpeechSynthesisUtterance(text);
        msg.lang = "de-DE";

        // Stimmen laden (asynchron!)
        function speakWithGoogleVoice() {{
            const voices = window.speechSynthesis.getVoices();
            // Google Deutsch Stimme auswählen, fallback: erste deutsche Stimme
            let voice = voices.find(v => v.lang === 'de-DE' && v.name.includes('Google'));
            if (!voice) {{
                voice = voices.find(v => v.lang === 'de-DE');
            }}
            msg.voice = voice;

            // Vorherige Sprachausgabe stoppen und neue starten
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(msg);
        }}

        // Manche Browser laden Stimmen asynchron, daher Timeout / event
        if (window.speechSynthesis.getVoices().length === 0) {{
            window.speechSynthesis.onvoiceschanged = speakWithGoogleVoice;
        }} else {{
            speakWithGoogleVoice();
        }}
    </script>
    """,
    height=0,
)

# Statistiken berechnen (GECACHT!)
stats = berechne_statistiken(spieler, bonus_empfaenger_pro_runde, punkteverlauf)

# ==================== ANZEIGE ====================

# Punktetabelle
st.subheader("📊 Aktueller Punktestand")
tabelle = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
    for i, runde in reversed(list(enumerate(daten["runden"]))):
    #for i, runde in enumerate(daten["runden"]):
        bonus = "★" if i > 0 and sp["name"] == bonus_empfaenger_pro_runde[i] else ""
        zeile[runde["name"]] = f"E: {sp['einsaetze'][i]} | P: {sp['plaetze'][i]} | +{round(sp['gewinne'][i],1)}{bonus}"
    tabelle.append(zeile)

df = pd.DataFrame(tabelle)
st.dataframe(df, use_container_width=True, hide_index=True)

# Kommentar
st.subheader("💬 Spielkommentar")
for zeile in kommentar.split("\n"):
    if zeile.strip():
        st.markdown(zeile.strip())

# Verlaufsgrafik
st.subheader("📈 Punkteverlauf")
df_chart = pd.DataFrame(punkteverlauf)

chart = alt.Chart(df_chart).mark_line(point=True).encode(
    x="Runde",
    y=alt.Y("Punkte", scale=alt.Scale(zero=False)),
    color="Spieler",
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)

# Statistiken
st.subheader("📌 Spielstatistiken")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🏆 Häufigster Rundensieger", 
              stats["haeufigster_rundensieger"], 
              f"{stats['rundensieger_anzahl']}×")

with col2:
    st.metric("💯 Höchster Punktestand ever", 
              stats["max_punkte_spieler"], 
              f"{stats['max_punkte']:.1f} ({stats['max_punkte_runde']})")

with col3:
    st.metric("🎁 Häufigster Rubber-Banding-Nutzer", 
              stats["haeufigster_bonus_spieler"], 
              f"{stats['bonus_anzahl']}×")

with col4:
    st.metric("🎲 Risikofreudigster Spieler", 
              stats["risikofreudigster_spieler"], 
              f"{stats['max_durchschnitt_einsatz']:.1f} Ø Einsatz")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("📈 Effektivster Spieler", 
              stats["effektivster_spieler"], 
              f"{stats['effizienz_wert']:.2f} Gewinn/Einsatz")

with col6:
    st.metric("🔁 Konstanter Punktesammler", 
              f"{stats['konstantester_spieler']} ({stats['konstanter_gewinn']:.1f})", 
              "Ø Rundengewinn")

with col7:
    st.metric("🎯 Bonus-Effizienz", 
              f"{stats['bester_bonusnutzer']} ({stats['bester_bonusnutzer_anzahl']})", 
              "Bonus führte zum Rundensieg")

with col8:
    st.metric("📊 Spannungsindex", 
              f"±{stats['spannungsindex']:.2f}", 
              "Punkte-Streuung")

