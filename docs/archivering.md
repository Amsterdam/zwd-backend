# Archiveren van zaken

Dit document legt uit hoe zaken worden opgeschoond als hun bewaartermijn is verlopen (ticket WON-848). Het is geschreven voor iedereen die met de Django admin werkt, ook als je geen ontwikkelaar bent.

## Waarom archiveren?

We mogen persoonsgegevens en documenten niet langer bewaren dan nodig is. Na afloop van een vaste bewaartermijn wordt daarom een groot deel van een zaak verwijderd. De zaak zelf (metadata) blijft bestaan met de basisgegevens en het resultaat. Zo kunnen we later nog zien dat er een zaak was en hoe die is afgelopen, maar zonder de persoonlijke details.

## Hoe lang wordt een zaak bewaard?

Dat hangt af van hoe de zaak is afgesloten:

| Hoe is de zaak afgesloten? | Bewaartermijn |
|---|---|
| Succesvol afgerond (bijvoorbeeld HBO, advies of activatieteam) | 5 jaar |
| Eerder afgebroken of afgewezen | 1 jaar |
| Geen resultaat geregistreerd (afgesloten zaak zonder afsluitreden, zoals oude geïmporteerde zaken) | 5 jaar |

Of een zaak succesvol is, volgt uit de afsluitreden die bij het afsluiten is gekozen. Is er geen resultaat geregistreerd, dan gaan we ervan uit dat de zaak succesvol was. Zo'n zaak telt dus overal mee als succesvol: in de filter, in de Excelexport (kolom *Succesvol* is *Ja*, kolom *Resultaat* is *Geen resultaat geregistreerd*) en bij het archiveren.

**De termijn telt in hele kalenderjaren.** De termijn begint op 1 januari van het jaar ná de einddatum en eindigt op 31 december. Een voorbeeld:

- Een zaak wordt op 21 oktober 2026 afgebroken (bewaartermijn 1 jaar).
- De termijn loopt tot en met 31 december 2027.
- Vanaf 1 januari 2028 mag de zaak worden gearchiveerd.

Zaken die nog niet zijn afgesloten hebben geen bewaartermijn en kunnen niet worden gearchiveerd.

## Wat wordt verwijderd en wat blijft bewaard?

### Dit wordt definitief verwijderd

- **Documenten**, inclusief de bestanden zelf
- **Taakgeschiedenis:** alle ingevulde formulieren van afgeronde taken, ook factuurgegevens zoals inkoopordernummers en bedragen
- **Tijdlijn:** alle gebeurtenissen van de zaak
- **Workflows en openstaande taken**, voor zover die er nog zijn
- **Contactpersonen van de VvE**, maar alleen als de VvE geen andere zaak meer heeft die nog niet gearchiveerd is (zie hieronder)

### Dit blijft bewaard

- **De zaak zelf**, met alle velden. Er komt alleen een datum bij: *gearchiveerd op*.
- **De afsluitreden** (het resultaat) en de toelichting daarbij
- **De gegevens van het activatieteam:** type, onderwerp en vergaderdatum
- **De VvE**, inclusief eigenaren. Een VvE wordt nooit verwijderd.
- **De communicatienotities van de VvE**

### Wanneer worden contactpersonen verwijderd?

Contactpersonen horen bij een VvE, niet bij één zaak. Een VvE kan meerdere zaken hebben. De contactpersonen worden daarom alleen verwijderd als **alle** zaken van de VvE gearchiveerd zijn.

Heeft de VvE nog een andere zaak die open is, of een zaak die nog niet gearchiveerd is, dan blijven de contactpersonen staan. Ze worden dan verwijderd zodra die laatste zaak ook gearchiveerd wordt.

> **Let op:** archiveren kan niet ongedaan worden gemaakt. Heb je de factuurgegevens of andere informatie nog nodig, exporteer die dan eerst (zie stap 2 hieronder).

## Hoe archiveer je zaken?

Archiveren gebeurt in de Django admin, op de lijst met zaken (`/admin/cases/case/`). Iedereen met toegang tot die pagina kan het doen. In de zwd-frontend zit geen knop hiervoor.

1. **Zoek de zaken op.** Kies rechts bij de filter **Bewaartermijn** de optie **Alle verlopen bewaartermijnen**. Je kunt ook kiezen voor:
   - *Verlopen: succesvol of geen resultaat (5 jaar)*
   - *Verlopen: afgebroken (1 jaar)*
   - *Lopende bewaartermijn*: afgesloten zaken waarvan de termijn nog niet voorbij is

   Gearchiveerde zaken vallen buiten deze filters.

2. **Exporteer de zaken eerst (aanbevolen).** Selecteer de zaken en kies de actie **Geselecteerde zaken exporteren naar Excel**. Je krijgt een Excelbestand met per zaak onder andere de VvE, de einddatum, het resultaat, de bewaartermijn, de datum waarop die verloopt en de selectiecategorie (*21.1* bij 5 jaar, *21.2* bij 1 jaar). Bewaar dit bijvoorbeeld als vernietigingsverslag.

3. **Start het archiveren.** Selecteer de zaken (of alles) en kies de actie **Zaken met verlopen bewaartermijn archiveren**.

4. **Controleer het overzicht.** Je krijgt eerst een overzichtspagina. Daarop is nog niets gewijzigd: het is een proefrun. Je ziet:
   - hoeveel zaken worden gearchiveerd
   - hoeveel documenten, taken, tijdlijngebeurtenissen en contactpersonen worden verwijderd
   - bij welke VvE's de contactpersonen blijven staan, en waarom
   - welke zaken worden overgeslagen, en waarom

5. **Bevestig of annuleer.** Klik op **Bevestigen en archiveren** om door te gaan, of op **Annuleren** om niets te doen. Na het archiveren zie je een melding met de aantallen.

### Welke zaken worden overgeslagen?

Je kunt gerust een ruime selectie maken. Zaken die niet gearchiveerd mogen worden, worden automatisch overgeslagen:

- **Nog niet afgesloten:** de zaak loopt nog.
- **Afgesloten, maar de bewaartermijn loopt nog**
- **Al eerder gearchiveerd**

Kan geen enkele geselecteerde zaak worden gearchiveerd, dan zegt de overzichtspagina dat, en is er alleen een knop om terug te gaan.

### Wat als er iets misgaat?

Elke zaak wordt apart gearchiveerd. Gaat er halverwege iets mis, dan blijven de zaken die al klaar waren gewoon gearchiveerd en worden de overige zaken niet aangeraakt. Je kunt de actie daarna opnieuw uitvoeren. De zaken die al gearchiveerd zijn, worden dan overgeslagen.

Een bestand wordt pas uit de opslag verwijderd als het archiveren van die zaak gelukt is. Er ontstaat dus nooit een zaak waarvan het bestand weg is terwijl de rest nog bestaat.

## Voor ontwikkelaars

| Bestand | Wat staat erin |
|---|---|
| `app/apps/cases/retention.py` | Bewaartermijnen, berekening van de einddatum en de filters voor verlopen en lopende termijnen |
| `app/apps/cases/archive.py` | `build_archive_plan()` bepaalt wat er gebeurt (gebruikt voor zowel de proefrun als het uitvoeren), `archive_case()` schoont één zaak op, `delete_hoa_contacts()` verwijdert contactpersonen van een VvE |
| `app/apps/cases/admin.py` | De Excelexport, de filter *Bewaartermijn* en de archiveeractie |
| `app/apps/cases/templates/admin/cases/case/archive_confirmation.html` | De overzichtspagina |
| `app/apps/cases/tests/tests_archive.py` | Tests voor het archiveren |

Een paar technische keuzes:

- `archived_at` wordt gezet via `Case.objects.filter(...).update()` en niet via `case.save()`. `Case.save()` maakt automatisch een tijdlijngebeurtenis aan, waardoor de tijdlijn na het archiveren niet leeg zou zijn.
- Bij **alles selecteren** stuurt de overzichtspagina niet elk zaak-ID mee, maar gebruikt Django's `select_across`. Zo blijft het formulier onder de standaardlimiet van 1000 velden.
- Er is geen management command en geen automatische periodieke taak. Archiveren gebeurt alleen handmatig via de admin.
