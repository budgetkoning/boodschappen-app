# Boodschappen-app (eerste versie)

Een mobiele webapp/PWA met Flask en PostgreSQL, bedoeld om te publiceren op Render. Werkt op Android en iPhone via de browser en kan op geschikte browsers aan het startscherm worden toegevoegd.

## Wat zit erin?
- Eigen boodschappenlijst met herstelcode/token.
- Product toevoegen, hoeveelheid wijzigen bij invoer, afvinken en verwijderen.
- Keuze uit Lidl, Albert Heijn, Jumbo, Aldi en PLUS.
- Opslag in PostgreSQL op Render, zodat dezelfde lijst via de herstelcode op meerdere apparaten geopend kan worden.
- Basis-PWA manifest en service worker.

## Belangrijke beperkingen
- Dit is een eerste basisversie, nog niet onafhankelijk getest of live gepubliceerd.
- Supermarktkeuze is aanwezig, maar een actuele geverifieerde prijsfeed is nog niet aangesloten. De app toont dus geen verzonnen prijzen. Product- en prijsgegevens moeten nog via een betrouwbare, toegestane gegevensbron worden gekoppeld.
- Een herstelcode is een geheime toegangssleutel: wie hem heeft, kan de lijst openen. Dit is nog geen volwaardig account- en gebruikerssysteem.
- Voor distributie via Apple App Store/Google Play zijn later aanvullende stappen nodig. PWA-installatie is de eerste route.

## Publiceren op Render via GitHub
1. Maak op GitHub een **nieuwe lege repository** aan, bijvoorbeeld `boodschappen-app`. Voeg bij het aanmaken geen README, license of gitignore toe.
2. Upload alle bestanden en de `static`-map uit deze map naar de hoofdmap van de repository. `app.py`, `requirements.txt` en `render.yaml` moeten direct in de hoofdmap staan.
3. Open Render en kies **New + → Blueprint**. Koppel GitHub en kies de repository `boodschappen-app`.
4. Render leest `render.yaml`. Controleer de aangemaakte webservice en PostgreSQL-database en bevestig de deploy.
5. Wacht tot de deploy klaar is. Open de door Render gegeven `https://...onrender.com`-URL.
6. Test `/api/health`: de pagina moet JSON tonen met `"ok": true`.
7. Maak een lijst en voeg een product toe. Bewaar de herstelcode. Open de app op een tweede apparaat en kies **Ik heb al een herstelcode**.

## Lokale test (optioneel)
Python 3.11+ installeren, daarna:
```bash
pip install -r requirements.txt
python app.py
```
Open `http://localhost:10000`.

## Volgende ontwikkelstappen
1. Prijsbron vinden en toestemming/API-voorwaarden verifiëren.
2. Productmatching per winkel testen en voorkomen dat winkelresultaten door elkaar lopen.
3. Betere accounts/uitnodigingen en gedeelde lijsten bouwen.
4. App-iconen en installatietests op Android/iOS toevoegen.
