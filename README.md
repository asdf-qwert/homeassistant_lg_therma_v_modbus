## Description
This package is for connecting and controlling an LG Therma V heat pump with Homeassistant via Modbus RTU.  

You will find all information [here](https://github.com/basti242/homeassistant_lg_therma_v_modbus/wiki).

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
 



