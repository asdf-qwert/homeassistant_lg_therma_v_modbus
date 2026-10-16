## Description
This package is for connecting and controlling an LG Therma V heat pump with Homeassistant via Modbus RTU.  

You will find all information [here](https://github.com/basti242/homeassistant_lg_therma_v_modbus/wiki).

## Počty startů kompresoru

Počty startů za den, týden, měsíc a rok se ukládají pomocí `utility_meter`
z přírůstků `sensor.hp_compressor_starts_total`. Nezávisí na délce historie
v recorderu a zůstávají zachované po restartu. Roční počet se nuluje
1. ledna o půlnoci, měsíční první den měsíce, týdenní v pondělí a denní
každou půlnoc podle časového pásma Home Assistantu.

Původní `history_stats` přepočítával počty pouze z dosud uchované historie;
po jejím promazání mohl proto klesnout i počet za aktuální rok. Navíc
počítal běžící kompresor na začátku období jako start. Nové počítání
zvyšuje celkový čítač pouze při přechodu `off` → `on`. Návrat z `unknown`
nebo `unavailable` do `on` už nepřidává falešný start; starty během výpadku
komunikace nebo vypnutého Home Assistantu nelze zpětně zjistit.

### Přechod ze starých počtů

Aktualizujte oba YAML soubory, zkontrolujte konfiguraci a restartujte Home
Assistant. Dashboard nyní používá nové entity:

| Období | Nová entita |
| --- | --- |
| Den | `sensor.hp_compressor_starts_daily` |
| Týden | `sensor.hp_compressor_starts_weekly` |
| Měsíc | `sensor.hp_compressor_starts_monthly` |
| Rok | `sensor.hp_compressor_starts_yearly` |

Původní entity s koncovkami `_today`, `_week`, `_month` a `_year` se už
nepočítají. Vlastní karty a automatizace přesměrujte na nové entity;
nepotřebné staré entity můžete odstranit v nastavení entit. Celkový čítač
ani jeho senzor se nemění a kvůli přechodu je neresetujte.

Nové měřiče začínají počítat od nasazení, nikoli zpětně od začátku období.
Pro zachování dosavadních počtů použijte v **Vývojářské nástroje → Akce**
akci `utility_meter.calibrate`, vyberte příslušnou novou entitu a nastavte
ověřený počet pro její aktuální období. Kalibrace se dělá pro každé období
zvlášť a pak se nové starty dál přičítají. Hodnotu neodvozujte z již
zkráceného `history_stats`; smazaná historie se touto opravou neobnoví.

Podrobnosti: [omezení History Stats](https://www.home-assistant.io/integrations/history_stats/#duration)
a [trvalé měřiče Utility Meter](https://www.home-assistant.io/integrations/utility_meter/).

## Odmrazování a spotřeba energie

Odmrazování se nezapočítává do chlazení. Jeho elektrická spotřeba patří do
topení; pokud je současně aktivní ohřev TUV, patří do TUV. Chlazení vyžaduje
záporný rozdíl teplot vody, vypnuté odmrazování a režim LG Chlazení nebo Auto.
Záporná delta při topení ani těsně po odmrazování v režimu Topení tedy chlazení
nespustí. Během odmrazování se tepelný výkon vykazuje jako 0, aby odebrané
teplo nezvyšovalo vyrobenou energii ani COP. Odebrané teplo se od vyrobené
energie neodečítá.

Po aktualizaci `modbus_lg_heatpump.yaml` zkontrolujte konfiguraci a restartujte
Home Assistant. Oprava platí pro nové měření; dříve uloženou spotřebu mezi
topením a chlazením automaticky nepřerozdělí.

## Krb – útlum teploty vody

Přepínač `input_boolean.hp_fireplace_mode` už podlahovku nevypíná ani neblokuje
její zapnutí. V režimu **Auto klima → Topení** snižuje vypočtenou cílovou teplotu
vody o `input_number.hp_fireplace_reduction`. V dashboardu v Parametrech křivky
nastavte například **3 °C** pro posun **−3 °C**. Nový pomocník začíná na 0 °C
(bez snížení); po restartu si ponechá nastavenou hodnotu.

Výpočet je `max(minimum vody, křivka + solární korekce + korekce místnosti + posun − snížení krbem)`.
Zůstává zachováno minimum topné křivky a při krbu také minimum HC1 20 °C.
Například požadavek 28 °C se snížením 3 °C klesne na 25 °C; při minimu 24 °C
neklesne pod 24 °C. Během krbového režimu se i pokles požadavku zapisuje ihned,
bez běžného hodinového čekání. Chlazení a TUV tato korekce nemění.

Při poklesu naměřené pokojové teploty na cílovou se krbový režim automaticky
vypne jako dříve. Samotné ukončení útlumu nezapíná hlavní vypínač: chod dál
řídí běžná regulace včetně venkovního cutoffu. Bez Auto klima se automatická
korekce vody neaplikuje.

Jde o snížení požadavku na ohřev, nikoli o samostatné ovládání oběhového
čerpadla nebo zákaz kompresoru. Balíček stav čerpadla pouze čte; jeho skutečný
chod při dosažené teplotě vody závisí na nastavení a regulaci LG.

Po aktualizaci obou YAML souborů zkontrolujte konfiguraci a restartujte Home
Assistant, aby se odstranila i původní automatizace
`hp_automation_fireplace_mode_on`. Před prvním použitím nastavte snížení vody.
 



