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

st.set_page_config(page_title="📺 Live Spielstand", layout="wide")

# Auto-Refresh alle 5 Minuten (300.000 Millisekunden)
streamlit_autorefresh.st_autorefresh(interval=300_000, key="refresh")

# 🔒 Fester Spielname – HIER ANPASSEN!
FESTER_SPIELNAME = "Wintervatertagsspiele2025"

# Firebase verbinden
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.title("🎲 Vatertagsspiele 2025 - Spielstand (live)")

# Spiel laden
spiel_doc = db.collection("spiele").document(FESTER_SPIELNAME).get()
if not spiel_doc.exists:
    st.error(f"Spiel '{FESTER_SPIELNAME}' nicht gefunden.")
    st.stop()

daten = spiel_doc.to_dict()
spieler = daten["spieler"]
multiplikatoren = daten["multiplikatoren"]
runden = daten["runden"]
rundendaten = []
kommentare = daten.get("kommentare", [])

# Punkte berechnen
for sp in spieler:
    sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
    sp["punkte"] = 20.0

punkteverlauf = []
zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}

bonus_empfaenger_pro_runde = []

for i, runde in enumerate(runden):
    rundenname = runde["name"]
    rundenzeit = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S")

    letzter_spieler = min(zwischenpunkte, key=zwischenpunkte.get)
    bonus_empfaenger_pro_runde.append(letzter_spieler)

    gewinne_der_runde = []

    for sp in spieler:
        einsatz = runde["einsaetze"].get(sp["name"], 0)
        platz = runde["plaetze"].get(sp["name"], 1)
        multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0
        gewinn = einsatz * multiplikator

        # Rubber-Banding: Kein Punktverlust für den Letztplatzierten der VORHERIGEN Runde
        if sp["name"] == letzter_spieler and gewinn < 0:
            gewinn = 0

        sp["einsaetze"].append(einsatz)
        sp["plaetze"].append(platz)
        sp["gewinne"].append(gewinn)
        sp["punkte"] += gewinn
        zwischenpunkte[sp["name"]] += gewinn
        gewinne_der_runde.append((sp["name"], gewinn))
        punkteverlauf.append({
            "Runde": f"{i+1}: {runde['name']}",
            "Spieler": sp["name"],
            "Punkte": zwischenpunkte[sp["name"]]
        })

    rundendaten.append({
    "runde": runde["name"],
    "zeit": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S"),
    "fuehrender": max(zwischenpunkte, key=zwischenpunkte.get),
    "letzter": min(zwischenpunkte, key=zwischenpunkte.get),
    "rundensieger": max(
        [(sp["name"], sp["gewinne"][i]) for sp in spieler],
        key=lambda x: x[1]
    ),
    "bonus": bonus_empfaenger_pro_runde[i],
})


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
"🏇 **{name}** galoppiert dem Feld davon – {punkte:.1f} Punkte auf dem Konto!",
]

kommentare_letzter = [
    "🐢 **{name}** hinkt mit {punkte:.1f} Punkten hinterher. Vielleicht war das ein geheimer Plan?",
    "🪨 **{name}** hält das Feld stabil von hinten – {punkte:.1f} Punkte und viel Luft nach oben.",
    "🌌 **{name}** ist auf Entdeckungsreise im unteren Punktesektor ({punkte:.1f}).",
    "🕳️ **{name}** erkundet die Tiefen der Punktetabelle mit {punkte:.1f} Punkten, ganz ohne Eile.",
"🐌 **{name}** nimmt das Rennen gelassen – {punkte:.1f} Punkte und jede Menge Potenzial!",
"🧊 **{name}** bleibt cool am Tabellenende mit {punkte:.1f} Punkten, vielleicht kommt der große Sprung noch?",
"🌱 **{name}** wächst langsam, aber stetig – {punkte:.1f} Punkte sind erst der Anfang.",
"🪁 **{name}** schwebt am unteren Rand mit {punkte:.1f} Punkten, bereit für den Aufwind?",
"🛸 **{name}** funkt aus der unteren Liga – {punkte:.1f} Punkte und eine Mission im Gange.",
"🦥 **{name}** bewegt sich gemächlich mit {punkte:.1f} Punkten, aber unterschätze nie den Spätstarter!",
"🧭 **{name}** sucht noch den Weg zum Punktetriumph – aktuell bei {punkte:.1f} Punkten.",
"🎒 **{name}** sammelt Erfahrung am Tabellenende – {punkte:.1f} Punkte sind nur der Anfang.",
"🪶 **{name}** landet sanft auf dem letzten Platz mit {punkte:.1f} Punkten, aber wer weiß, wie lange noch?",
]

kommentare_rundensieger = [
    "💥 **{name}** schnappt sich diese Runde mit +{gewinn:.1f} Punkten. Boom!",
    "🔥 **{name}** dominiert die Runde! +{gewinn:.1f} Punkte sind kein Zufall.",
    "🎯 **{name}** trifft ins Schwarze – +{gewinn:.1f} Punkte in einer Runde!",
    "⚡ **{name}** zündet den Turbo und holt +{gewinn:.1f} Punkte, was für ein Move!",
"🏹 **{name}** zielt perfekt – +{gewinn:.1f} Punkte gehen direkt aufs Konto!",
"🚀 **{name}** hebt ab und landet +{gewinn:.1f} Punkte, das war galaktisch!",
"🎉 **{name}** feiert den Rundensieg mit +{gewinn:.1f} Punkten, verdient und eindrucksvoll!",
"🧨 **{name}** lässt es krachen – +{gewinn:.1f} Punkte in einem Durchgang!",
"🏆 **{name}** holt sich den Pokal dieser Runde mit +{gewinn:.1f} Punkten, stark gespielt!",
"🕶️ **{name}** bleibt cool und punktet +{gewinn:.1f}, ein echter Profi!",
"🧠 **{name}** spielt clever und sichert sich +{gewinn:.1f} Punkte, Strategie zahlt sich aus!",
"🎲 **{name}** würfelt das Glück auf seine Seite – +{gewinn:.1f} Punkte!",
"🦾 **{name}** zeigt Stärke und holt +{gewinn:.1f} Punkte, eine Maschine auf dem Spielfeld!",
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
    "⚡ **{name}** nutzt Rubber-Banding und rasiert die Runde mit +{gewinn:.1f} Punkten!",
    "👀 **{name}** kommt von hinten – mit Bonus +{gewinn:.1f} Punkte! Da staunt das Feld.",
    "🧨 **{name}** startet durch! Rubber-Banding at its best: +{gewinn:.1f} Punkte!",
    "🚀 **{name}** zündet den Nachbrenner und holt +{gewinn:.1f} Punkte, das ist Comeback-Power!",
"🎮 **{name}** spielt Reverse-Mode – von hinten nach vorn mit +{gewinn:.1f} Punkten!",
"🦘 **{name}** springt aus dem Schatten und kassiert +{gewinn:.1f} Punkte, das nennt man Timing!",
"🧃 **{name}** tankt Bonusenergie und liefert +{gewinn:.1f} Punkte ab, das war stark!",
"🎢 **{name}** fährt Achterbahn – ganz unten gestartet, ganz oben gelandet mit +{gewinn:.1f} Punkten!",
"🕹️ **{name}** aktiviert den Comeback-Code – +{gewinn:.1f} Punkte aus dem Nichts!",
"🪂 **{name}** landet punktgenau – +{gewinn:.1f} Punkte aus der Tiefe des Feldes!",
"🧬 **{name}** mutiert zum Rundensieger – +{gewinn:.1f} Punkte durch Bonus-Evolution!",
"🎯 **{name}** trifft aus dem Off – +{gewinn:.1f} Punkte und alle schauen verdutzt!",
"🦾 **{name}** zeigt Comeback-Qualitäten – +{gewinn:.1f} Punkte und plötzlich ganz vorn!",
]

# Kommentare generieren
aktueller_fuehrender = max(zwischenpunkte, key=zwischenpunkte.get)
aktueller_letzter = min(zwischenpunkte, key=zwischenpunkte.get)
rundensieger = max(gewinne_der_runde, key=lambda x: x[1])
bonus_empfaenger = letzter_spieler

kommentare_roh = daten.get("kommentare", [])
kommentare = []
neue_kommentare = []
bereits_kommentierte_runden = {k["runde_index"] for k in kommentare}

for j, rd in enumerate(rundendaten):
    if j in bereits_kommentierte_runden:
        continue  # Kommentar existiert bereits, überspringen

    # Kommentarblock generieren
    kommentarblock = f"### 🕓 Runde {j+1}: *{rd['runde']}* ({rd['zeit']})\n"
    kommentarblock += "- " + random.choice(kommentare_fuehrend).format(
        name=rd["fuehrender"], punkte=zwischenpunkte[rd["fuehrender"]]
    ) + "\n"
    kommentarblock += "- " + random.choice(kommentare_letzter).format(
        name=rd["letzter"], punkte=zwischenpunkte[rd["letzter"]]
    ) + "\n"
    kommentarblock += "- " + random.choice(kommentare_rundensieger).format(
        name=rd["rundensieger"][0], gewinn=rd["rundensieger"][1]
    ) + "\n"

    if rd["bonus"] == rd["rundensieger"][0]:
        kommentarblock += "- " + random.choice(kommentare_bonus_gewinnt).format(
            name=rd["bonus"], gewinn=rd["rundensieger"][1]
        ) + "\n"
    else:
        kommentarblock += "- " + random.choice(kommentare_bonus).format(
            name=rd["bonus"]
        ) + "\n"

    neue_kommentare.append({
        "runde_index": j,
        "runde_name": rd["runde"],
        "text": kommentarblock
    })

# Nur speichern, wenn es neue Kommentare gibt
# from firebase_admin import firestore

# if neue_kommentare:
#    db.collection("spiele").document(FESTER_SPIELNAME).update({
#        "kommentare": firestore.ArrayUnion(neue_kommentare)
#    })


# Punktetabelle anzeigen
st.subheader("📊 Aktueller Punktestand")
tabelle = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
   # for i in range(len(runden)):
    for i in range(len(runden) - 1, -1, -1):
        bonus = "★" if sp["name"] == bonus_empfaenger_pro_runde[i] else ""
        zeile[runden[i]["name"]] = f"E: {sp['einsaetze'][i]} | P: {sp['plaetze'][i]} | +{round(sp['gewinne'][i],1)}{bonus}"
    tabelle.append(zeile)

df = pd.DataFrame(tabelle)
st.dataframe(df, use_container_width=True, hide_index=True)

# Aktuellen Kommentar anzeigen
st.subheader("💬 Spielkommentar")
if kommentare:
    st.markdown(kommentare[-1]["text"])
else:
    st.info("Noch kein Kommentar verfügbar.")

# Verlaufsgrafik
st.subheader("📈 Punkteverlauf")
df_chart = pd.DataFrame(punkteverlauf)

# Nur Runden bis zur vorletzten Runde behalten
max_runden_index = len(runden) - 2  # da 0-basiert, -2 = vorletzte Runde
# Runde ist String wie "1: XYZ", wir filtern nach der Rundenzahl vor dem Doppelpunkt

#df_chart = df_chart[df_chart["Runde"].apply(
#    lambda r: int(r.split(":")[0]) <= max_runden_index + 1  # +1 da Runde 1-basiert
#)]

chart = alt.Chart(df_chart).mark_line(point=True).encode(
    x="Runde",
    y=alt.Y("Punkte", scale=alt.Scale(zero=False)),
    color="Spieler",
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)

# 📊 Spielstatistiken anzeigen
st.subheader("📌 Spielstatistiken")

# 1. Häufigster Rundensieger
rundensieger_namen = [runde["rundensieger"][0] for runde in rundendaten]
rundensieger_counts = pd.Series(rundensieger_namen).value_counts()
haeufigster_rundensieger = rundensieger_counts.idxmax()
rundensieger_anzahl = rundensieger_counts.max()

# 2. Höchster Punktestand im Spielverlauf
df_punkte_max = pd.DataFrame(punkteverlauf)
max_row = df_punkte_max.loc[df_punkte_max["Punkte"].idxmax()]
max_punkte = max_row["Punkte"]
max_punkte_spieler = max_row["Spieler"]
max_punkte_runde = max_row["Runde"]

# 3. Häufigster Rubber-Banding-Spieler (Bonus-Empfänger)
bonus_daten = bonus_empfaenger_pro_runde[1:]  # Erste Runde ausschließen
if bonus_daten:
    bonus_counter = pd.Series(bonus_daten)
    haeufigster_bonus_spieler = bonus_counter.value_counts().idxmax()
    bonus_anzahl = bonus_counter.value_counts().max()
else:
    haeufigster_bonus_spieler = "–"
    bonus_anzahl = 0

# 4. Risiko-Freudigster Spieler – Höchster durchschnittlicher Einsatz
einsatz_durchschnitt = {
    sp["name"]: sum(sp["einsaetze"]) / len(sp["einsaetze"]) if sp["einsaetze"] else 0
    for sp in spieler
}
risikofreudigster_spieler = max(einsatz_durchschnitt, key=einsatz_durchschnitt.get)
max_durchschnitt_einsatz = einsatz_durchschnitt[risikofreudigster_spieler]

# 5. Effektivster Spieler – Gewinn/Einsatz-Verhältnis
effizienz = {}
for sp in spieler:
    gesamt_einsatz = sum(sp["einsaetze"])
    gesamt_gewinn = sum(sp["gewinne"])
    if gesamt_einsatz > 0:
        effizienz[sp["name"]] = gesamt_gewinn / gesamt_einsatz
    else:
        effizienz[sp["name"]] = 0
effektivster_spieler = max(effizienz, key=effizienz.get)
effizienz_wert = effizienz[effektivster_spieler]

# 6. Durchschnittlicher Rundengewinn – Wer punktet konstant?
gewinn_durchschnitt = {
    sp["name"]: sum(sp["gewinne"]) / len(sp["gewinne"]) if sp["gewinne"] else 0
    for sp in spieler
}
konstantester_spieler = max(gewinn_durchschnitt, key=gewinn_durchschnitt.get)
konstanter_gewinn = gewinn_durchschnitt[konstantester_spieler]

# 7. Bonus-Effizienz – Wer nutzt den Bonus am besten?
bonus_sieger = {}
for r in rundendaten[1:]:  # Erste Runde ausschließen
    if r["bonus"] == r["rundensieger"][0]:
        name = r["bonus"]
        bonus_sieger[name] = bonus_sieger.get(name, 0) + 1

if bonus_sieger:
    bester_bonusnutzer = max(bonus_sieger, key=bonus_sieger.get)
    bester_bonusnutzer_anzahl = bonus_sieger[bester_bonusnutzer]
else:
    bester_bonusnutzer = "–"
    bester_bonusnutzer_anzahl = 0

# 8. Spannungsindex – Standardabweichung der aktuellen Punktestände
punkte_liste = [sp["punkte"] for sp in spieler]
spannungsindex = pd.Series(punkte_liste).std()


# Darstellung in vier Spalten und 2 Zeilen
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏆 Häufigster Rundensieger", f"{haeufigster_rundensieger}", f"{rundensieger_anzahl}×")

with col2:
    st.metric("💯 Höchster Punktestand ever", f"{max_punkte_spieler}", f"{max_punkte:.1f} Punkte ({max_punkte_runde})")

with col3:
    st.metric("🎁 Häufigster Rubber-Banding-Nutzer", f"{haeufigster_bonus_spieler}", f"{bonus_anzahl}×")

with col4:
    st.metric("🎲 Risikofreudigster Spieler", risikofreudigster_spieler, f"{max_durchschnitt_einsatz:.1f} Ø Einsatz")

col5, col6, col7, col8 = st.columns(4)

with col5:
    st.metric("📈 Effektivster Spieler", effektivster_spieler, f"{effizienz_wert:.2f} Gewinn/Einsatz")

with col6:
    st.metric("🔁 Konstanter Punktesammler", f"{konstantester_spieler} ({konstanter_gewinn:.1f})", "Ø Rundengewinn")


with col7:
    st.metric("🎯 Bonus-Effizienz", f"{bester_bonusnutzer} ({bester_bonusnutzer_anzahl})", "Bonus führte zum Rundensieg")

with col8:
    st.metric("📊 Spannungsindex", "±{:.2f}".format(spannungsindex), "Punkte-Streuung")

#st.subheader("💬 Spielkommentare")
#for kommentar in kommentare[:-1]:  # alle außer dem letzten
#    with st.expander(kommentar["text"].split("\n")[0]):
#        st.markdown("\n".join(kommentar["text"].split("\n")[1:]))

#aktuelle_runde_index = len(runden) - 1  # Index der letzten Runde (0-basiert)
#aktuelle_runde_name = f"{len(runden)}: {runden[-1]['name']}"
