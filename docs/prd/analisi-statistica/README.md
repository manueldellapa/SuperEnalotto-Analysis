# PRD — Analisi statistica delle estrazioni storiche

Stato al 5 novembre 2026: M0 implementata; M1 e M2 pianificate, con specifiche
READY. Lo stato di consegna è distinto dalla Definition of Ready delle storie.
Baseline storica della proposta del 19 ottobre 2026: commit `cd4bc39`, package
`0.2.0`; all'epoca il comando di analisi non era disponibile. Baseline corrente
verificata nel checkout e su `main` GitHub: commit
[`56377a4`](https://github.com/manueldellapa/SuperEnalotto-Analysis/commit/56377a4be5f4b2399b891acd519c0c33a540c3ef),
package ancora `0.2.0`. Questa revisione aggiorna solo la documentazione.

## Problema, utenti e risultato atteso

Alla baseline storica chi usava il downloader disponeva di un CSV validato, ma
doveva scrivere strumenti propri per contare le uscite dei numeri, confrontarle
e restringere il periodo. M0 offre ora le frequenze sull'intera sorgente;
filtri temporali e classifiche restano gli incrementi pianificati M1 e M2.
La funzionalità serve a utenti del toolkit da terminale e sviluppatori Python
che vogliono esplorare i dati già scaricati.

Risultato: analisi descrittiva locale, ripetibile e verificabile, con frequenze
assolute, percentuali di presenza e classifiche. Ogni risultato rende evidente
quali estrazioni sono state considerate. Le frequenze storiche non devono
essere presentate come previsioni delle estrazioni successive.

## Evidenze del repository

L'analisi è partita dal grafo Graphify esistente, poi ha verificato le fonti e
i test pertinenti. Il grafo orienta la navigazione; i fatti sotto derivano dai
file della baseline corrente. L'assenza di PRD, ADR e struttura `docs/` rilevata
alla baseline storica precedeva la creazione di questi cinque documenti.

| Fatto verificato | Fonte canonica o evidenza |
| --- | --- |
| Il prodotto acquisisce dati, produce CSV e offre frequenze descrittive offline M0; filtri e classifiche non sono disponibili | [README](../../../README.md), [package e dipendenze](../../../pyproject.toml) |
| `Extraction` è frozen/slotted e definisce le dieci colonne CSV | [models.py](../../../src/superenalotto/models.py) |
| I validatori controllano valori, unicità della sestina e Jolly; costruire `Extraction` da solo non valida | [validators.py](../../../src/superenalotto/validators.py), [test](../../../tests/test_validators.py) |
| L'identità è `(extraction_date.year, contest_number)`; duplicati uguali collassano, conflitti interrompono | `deduplicate_extractions` in [pipeline.py](../../../src/superenalotto/pipeline.py), [test](../../../tests/test_pipeline.py) |
| `DataPaths` deriva i percorsi dalla radice scelta; il default distingue checkout e installazione | [paths.py](../../../src/superenalotto/paths.py), [test](../../../tests/test_paths.py) |
| Il CSV canonico è una sovrascrittura dell'intervallo scaricato; i fallimenti producono un CSV parziale distinto | README, [cli.py](../../../src/superenalotto/cli.py), [test](../../../tests/test_cli.py) |
| `load_extractions_csv` legge e valida il canonico, poi deduplica; `count_csv_rows` mantiene il solo conteggio righe | [pipeline.py](../../../src/superenalotto/pipeline.py), [test](../../../tests/test_pipeline.py) |
| `calculate_frequencies` è puro; `analysis_cli.main` compone lettura, calcolo e presentazione del report M0 | [analysis.py](../../../src/superenalotto/analysis.py), [analysis_cli.py](../../../src/superenalotto/analysis_cli.py), [test del calcolo](../../../tests/test_analysis.py), [test CLI](../../../tests/test_analysis_cli.py) |
| Python supportato: 3.14.x; CLI con `argparse`; pytest, monkeypatch e `tmp_path`, senza HTTP reale | pyproject.toml, [supporto test](../../../tests/support.py) |
| CI esegue Ruff, mypy strict e pytest da dipendenze bloccate | [ci.yml](../../../.github/workflows/ci.yml) |

### Issue correlate

Ricerca GitHub in sola lettura ripetuta il 5 novembre 2026, query
`repo:manueldellapa/SuperEnalotto-Analysis is:issue`: 15 issue restituite, nessuna
dedicata a frequenze, filtri o classifiche. Stati delle issue sotto verificati
individualmente. Le quattro storie non hanno issue dedicate, anche se M0 è
implementata; questa è una lacuna di copertura del tracker. Non crearle
automaticamente.

| Issue | Stato verificato | Relazione con il PRD |
| --- | --- | --- |
| [#1 — preservare il CSV canonico](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/1) | Chiusa | US-001 e US-002 devono preservarne le garanzie |
| [#6 — CLI installabile](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/6) | Chiusa | Convenzione riusata da US-002 |
| [#7 — directory configurabili](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/7) | Chiusa | `DataPaths` riusato da US-001 e US-002 |
| [#28 — identità per anno e concorso](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/28) | Chiusa | Regola riusata in US-001, anche oltre il cambio d'anno |
| [#29 — Jolly distinto dalla sestina](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/29) | Chiusa | Validazione riusata in US-001; SuperStar può coincidere |
| [#30 — smoke test wheel/sdist](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/30) | Aperta | Lavoro di distribuzione separato: coordinare il nuovo entry point se svolto; non blocca queste storie |

Le issue storiche possono descrivere versioni precedenti del dominio: in
particolare la chiave di [#5](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/5)
è stata superata dalla regola verificata di #28.
Questo PRD non ripropone i fix già presenti né include il completamento di #30.

## Perimetro e decisioni proposte

- Analizzare solo `DataPaths.extractions_csv`, senza download impliciti né
  fallback a `extractions.partial.csv`. Nessuna opzione per CSV arbitrari.
- Distinguere tre categorie: `main` (default), `jolly`, `superstar`; un report
  analizza una categoria. La sestina è aggregata senza distinguere posizione.
- Esporre un nuovo comando `superenalotto-analyze`, affiancato al downloader,
  e funzioni Python pure riutilizzabili per il calcolo.
- Offrire un intervallo di date inclusivo, opzionale su ciascun lato; nessun
  preset relativo a oggi. I filtri riguardano i dati disponibili, senza mutuare
  limiti o cascata anno/mese del downloader.
- Scrivere il report testuale su stdout; messaggi di errore su stderr. Testo
  dell'interfaccia in inglese, coerente con CLI e README esistenti.

Le scelte di M0 sono ora implementate; intervalli e classifiche rimangono
specifiche READY di M1/M2. La proposta storica non attestava preferenze
confermate dall'utente: questa revisione ne preserva le decisioni e distingue
le capacità disponibili da quelle pianificate, senza introdurre nuove scelte
funzionali. READY non equivale a consegna o approvazione di una release.

Esclusioni: predizioni, suggerimenti di gioco, ritardi, combinazioni/coppie,
test inferenziali, confronti automatici fra periodi, grafici, web UI, API HTTP,
database, scheduler, cache dei risultati, esportazioni JSON/CSV dei report,
migrazioni e modifiche ai workflow di release. Non aggiungere pandas, NumPy,
framework CLI o dipendenze di runtime per questa funzionalità.

## Requisiti funzionali canonici

Gli identificatori sotto sono l'unica definizione normativa dei requisiti.
Le storie specificano esempi osservabili e lavoro necessario, senza creare
requisiti concorrenti.

| ID | Requisito | Storia |
| --- | --- | --- |
| FR-001 | Leggere il CSV canonico UTF-8 con intestazione identica, anche nell'ordine, a `Extraction.CSV_FIELDNAMES`. Rifiutare intestazione assente, duplicata o diversa, righe con campi mancanti/eccedenti, valori interi non rappresentati da cifre decimali ASCII, date diverse da `YYYY-MM-DD` o non valide e testo non decodificabile. Validare ogni `Extraction` con i validatori esistenti; non saltare record invalidi. Un CSV con sola intestazione è valido e vuoto; un file di zero byte è invalido. | US-001 |
| FR-002 | Validare tutto il file e deduplicarlo prima dei filtri, usando `deduplicate_extractions`. Duplicati identici contano una volta; conflitti di data o payload per la stessa identità interrompono l'analisi, anche se fuori dal periodo richiesto. Mantenere concorsi con numero uguale in anni diversi. | US-001 |
| FR-003 | Per la categoria selezionata produrre 90 righe, una per numero 1–90, incluse frequenze nulle. Per `main`, contare ogni presenza nella sestina; Jolly e SuperStar contano solo nelle rispettive categorie. Non mescolare le categorie anche quando i valori coincidono. | US-002 |
| FR-004 | Dato `N` concorsi unici selezionati e `c(n)` presenze del numero, la percentuale di presenza è `100 × c(n) / N`. Per `N > 0`, la somma dei conteggi è `6N` in `main`, `N` nelle altre categorie; la somma delle percentuali non arrotondate è rispettivamente 600% o 100%. Per `N = 0`, conteggi zero e percentuali `N/A`, mai divisioni per zero. | US-002 |
| FR-005 | Ogni report dichiara percorso sorgente, categoria, estremi richiesti (o assenza di limiti), minimo/massimo delle date nel CSV deduplicato, minimo/massimo delle date selezionate e `N` prima dell'eventuale taglio classifica. Date effettive assenti si rappresentano con `N/A`. Dichiarare sempre che la copertura storica non è certificata e le statistiche sono descrittive, non previsioni; il solo CSV non prova continuità, completezza o aggiornamento. | US-002 |
| FR-006 | Accettare `--start-date` e `--end-date` come date ISO strette e reali: includere gli estremi, ammettere un solo limite e usare tutto il CSV se entrambi assenti. Rifiutare inizio successivo alla fine. Limiti esterni ai dati, anche futuri, sono ammessi e non generano record sintetici. Non dipendere da `date.today()`. | US-003 |
| FR-007 | Con selezione vuota emettere un report esplicito `No extractions in selected period`, `N = 0`, metadati e 90 conteggi a zero con percentuali `N/A` nell'ordine numerico. Se è richiesta una classifica, non emettere righe classificate e spiegare l'assenza di dati. L'esito è comunque positivo. | US-002, US-003, US-004 |
| FR-008 | Offrire ordinamento numerico predefinito, per più frequenti e per meno frequenti. Nelle classifiche, a conteggio pari precede il numero minore; includere anche gli zeri quando `N > 0`. Calcolare su tutti i concorsi selezionati e ordinare sui conteggi interi, senza ricalcoli o confronti sulle percentuali arrotondate. | US-004 |
| FR-009 | Nelle classifiche accettare un limite `--top K`, intero 1–90; senza limite mostrare tutti i 90 numeri. Restituire esattamente K righe per `N > 0`, anche con parità al confine. Rifiutare `--top` con ordinamento numerico. Le posizioni sono ordinali 1…K, senza ranghi condivisi. | US-004 |
| FR-010 | Registrare `superenalotto-analyze` con `main(argv=None)` e opzioni `--data-dir`, `--category main\|jolly\|superstar` (default `main`), poi i filtri di FR-006 e le opzioni `--order number\|most-frequent\|least-frequent` (default `number`) e `--top` di FR-008/009 nei rispettivi incrementi. Riutilizzare i default di `DataPaths`. Exit code: 0 per report valido/vuoto e help, 1 per errori di lettura/integrità, 2 per argomenti invalidi. In caso di errore non emettere un report parziale su stdout. | US-002, US-003, US-004 |

## Requisiti non funzionali

| ID | Vincolo verificabile | Copertura |
| --- | --- | --- |
| NFR-001 | Analisi offline e in sola lettura: nessuna chiamata HTTP, directory creata, file scritto o rimosso; canonico, parziale e cache restano identici anche su errore. | US-001, US-002 |
| NFR-002 | Conservare layering, firma/comportamento del downloader, schema CSV, identità e validatori. Nessuna dipendenza nuova o modifica di versione. | Tutte |
| NFR-003 | Stesso input e opzioni producono stessi dati e ordine indipendentemente dall'ordine iniziale delle righe. Mostrare percentuali con due decimali, punto decimale e arrotondamento solo nella presentazione; nessuna data corrente o timestamp nel report. | US-002, US-003, US-004 |
| NFR-004 | Errori leggibili, senza traceback per errori attesi. Per righe invalide indicare sorgente e riga CSV; per conflitti identità e dettagli dell'errore esistente. Nessun `skip` silenzioso o recupero HTTP. | US-001, US-002 |
| NFR-005 | Una sola lettura del CSV e un passaggio di conteggio dopo validazione/deduplicazione/selezione, con 90 contatori. Ammessi lista e ordinamento già usati dalla deduplicazione (`O(D log D)` per D righe); nessuna scansione completa per ogni numero e nessuna infrastruttura di caching. | US-001, US-002, US-004 |
| NFR-006 | Superare i gate esistenti con dipendenze bloccate; test locali deterministici con pytest, `tmp_path`, monkeypatch e helper esistenti, senza HTTP reale. | Tutte |

## Impatto e riuso dell'architettura

| Componente attuale | Stato M0 e impatto residuo M1/M2 |
| --- | --- |
| `pipeline.py` | Lettore CSV validato implementato con riuso di validazione e deduplicazione, senza rifattorizzare il download. Restituisce dati prima del calcolo e non applica filtri; preservare questo confine in M1/M2. |
| `models.py`, `validators.py`, `constants.py` | Riutilizzare `Extraction`, header e regole 1–90; nessuna migrazione o modifica dell'entità. |
| `paths.py` | Riutilizzare `DataPaths.extractions_csv`, senza percorsi globali o nuove cartelle dati. |
| `analysis.py` | Frequenze pure e contratti tipizzati `Frequency`/`FrequencyReport` implementati, senza disco/rete; precondizione di input valido e deduplicato documentata. M1 aggiungerà la selezione distinguendo contesto sorgente/selezione; M2 ordinerà i conteggi interi. Evitare gerarchie di servizi e protocolli generici. |
| `analysis_cli.py` | Parsing base, percorsi, composizione, formattazione ed exit code implementati. M1/M2 estenderanno solo questo parser con le rispettive opzioni, senza ampliare il downloader. |
| `pyproject.toml`, `tests/test_packaging.py` | Entry point di analisi registrato; il test verifica già entrambi i comandi, chiamabilità e argomenti Python opzionali. Preservare queste garanzie; smoke wheel/sdist distinto in #30. |
| Test e README | Test del lettore, calcolo, CLI e packaging e documentazione utente M0 presenti. M1/M2 estenderanno test e README nei rispettivi task; il rifiuto attuale delle opzioni future è intenzionale. |

Non serve database, schema nuovo, servizio esterno o migrazione. Il lettore è
stretto sul formato oggi scritto dal progetto; l'eventuale supporto a CSV di
terze parti richiederà un requisito successivo esplicito. Il nuovo comando non
deve alterare CLI, launcher, uscite o protezione del CSV parziale del downloader.

### Interfaccia finale proposta

Il primo esempio è disponibile in M0. Gli esempi M1/M2 descrivono l'interfaccia
pianificata e non sono ancora eseguibili; la scelta della categoria è già M0.

```bash
# M0 disponibile: frequenze di tutta la sorgente, numeri principali
superenalotto-analyze --data-dir ~/superenalotto-data

# M1 pianificata: periodo inclusivo e categoria separata
superenalotto-analyze --data-dir ~/superenalotto-data --category jolly \
  --start-date 2024-01-01 --end-date 2024-12-31

# M2 pianificata: primi dieci per frequenza nel periodo, oppure meno frequenti
superenalotto-analyze --start-date 2024-01-01 --order most-frequent --top 10
superenalotto-analyze --category superstar --order least-frequent --top 10
```

Il report ha un'intestazione con i metadati di FR-005 e una tabella `number`,
`count`, `presence_percent`; le classifiche aggiungono `position`. Non richiedere
un allineamento a colonne di larghezza fissa come contratto pubblico. Il messaggio
di copertura deve restare presente anche con un CSV canonico e senza parziale.

## Milestone e tracciabilità

M0–M2 sono incrementi locali di questo PRD, senza versione di release assegnata
e senza creare o rinominare milestone GitHub esistenti.

| Incremento | Stato di consegna al 5 novembre 2026 | Evidenza o prerequisito |
| --- | --- | --- |
| M0 | Implementata, TASK-001…004 completati | Commit `56377a4`, evidenze nelle storie US-001/002 e CI indicata sotto |
| M1 | Pianificata, TASK-005/006 da implementare | Specifica US-003 READY; prerequisito M0 consegnato |
| M2 | Pianificata, TASK-007/008 da implementare | Specifica US-004 READY; consegna integrata dopo M1, task puro dopo TASK-003 |

| ID | Risultato e criterio di uscita | Dipendenze | Storie e requisiti |
| --- | --- | --- | --- |
| M0 | Frequenze utilizzabili da CLI sull'intero CSV: ingresso validato, 90 numeri, categorie separate, percentuali e metadati verificati; gate verdi. US-001 è il prerequisito tecnico minimo incluso nello stesso incremento verticale di US-002. | Nessuna nuova dipendenza esterna | [US-001](stories/US-001-lettura-validata.md), [US-002](stories/US-002-frequenze.md); FR-001…005, FR-007, FR-010 (comando base); NFR-001…006 |
| M1 | Stesso report limitabile per data, con estremi e assenza di risultati corretti; nessuna regressione M0; gate verdi. | M0 | [US-003](stories/US-003-filtri-temporali.md); FR-006/007/010 (filtri), NFR-002/003/006 |
| M2 | Classifiche complete o top K, più/meno frequenti, parità e zeri deterministici anche con filtri; gate verdi. | M1 | [US-004](stories/US-004-classifiche.md); FR-007…010 (ordinamento/limite), NFR-002/003/005/006 |

Ordine delle storie: US-001 → US-002 → US-003 → US-004. I task puri sui filtri e
sulle classifiche possono essere preparati indipendentemente dopo il contratto
di conteggio di TASK-003; integrazione CLI e consegna seguono le milestone.

| Storia | Task atomici | Dipendenza di storia | Definition of Ready | Stato di consegna | Issue dedicata |
| --- | --- | --- | --- | --- | --- |
| US-001 | TASK-001, TASK-002 | Nessuna | READY | Implementata in M0 | Assente |
| US-002 | TASK-003, TASK-004 | US-001 | READY | Implementata in M0 | Assente |
| US-003 | TASK-005, TASK-006 | US-002 | READY | Pianificata per M1 | Assente |
| US-004 | TASK-007, TASK-008 | US-003 | READY | Pianificata per M2 | Assente |

READY significa che non manca una decisione per iniziare la storia quando i
prerequisiti sono consegnati; non significa che i predecessori siano già
implementati. I dettagli di criteri AC e verifiche risiedono nelle storie.

### Copertura dei requisiti per incremento

Questa tabella annota lo stato senza ridefinire FR/NFR. Le definizioni canoniche
e i criteri di uscita sopra restano invariati; nessun requisito trasversale è
considerato interamente consegnato per il solo completamento di M0.

| Requisiti | M0 implementata | M1 pianificata | M2 pianificata |
| --- | --- | --- | --- |
| [FR-001, FR-002](#requisiti-funzionali-canonici) | Lettura, validazione e deduplicazione dell'intera sorgente | Preservare le garanzie anche per record fuori filtro, US-003 | Preservare la stessa sorgente validata |
| [FR-003, FR-004, FR-005](#requisiti-funzionali-canonici) | Frequenze, percentuali e contesto senza limiti; sorgente e selezione coincidono | Applicare al campione filtrato e distinguere gli estremi, US-003 | Preservare metadati e denominatore prima del taglio, US-004 |
| [FR-006](#requisiti-funzionali-canonici) | Non disponibile | Filtri di US-003 | Riuso dei filtri |
| [FR-007](#requisiti-funzionali-canonici) | Vuoto su CSV con sola intestazione, ordine numerico | Vuoto prodotto dai filtri | Vuoto nelle classifiche |
| [FR-008, FR-009](#requisiti-funzionali-canonici) | Solo ordine numerico predefinito; classifiche, opzione `--order` e limite assenti | Preservare ordine numerico | Classifiche e limite di US-004 |
| [FR-010](#requisiti-funzionali-canonici) | Entry point, opzioni base ed exit code | Opzioni date e relativi errori | Opzioni ordine/limite e relativi errori |
| [NFR-001…006](#requisiti-non-funzionali) | Evidenze del lettore/calcolo/CLI e CI M0 | Preservare le garanzie M0; verificare filtri e regressioni previste in US-003 | Preservare M0/M1; verificare classifiche e regressioni previste in US-004 |

## Verifica e successo misurabile

Il completamento dell'intero PRD (M0–M2) richiede tutti i criteri AC delle quattro
storie soddisfatti, copertura di ogni FR e test su fixture con risultati noti:
invarianti `6N`/`N`, confini temporali, duplicati/conflitti, parità, assenza di
dati, errori e conservazione dei file. Nessuna dipendenza da archivio remoto o
dataset personale per provare correttezza.

Per ogni incremento implementato, con ambiente configurato come nel README:

```bash
uv sync --locked --all-extras
python -m ruff check .
python -m mypy src scripts tests
python -m pytest
```

Verificare anche lo stile con `python -m ruff format --diff .`, convenzione
locale aggiuntiva, senza descriverlo come gate CI. Per il comando introdotto in M0,
risincronizzare l'ambiente e verificarne `--help` e una fixture temporanea tramite
l'entry point installato. La verifica di wheel/sdist resta distinta (#30).

Evidenza funzionale preesistente, ricontrollata su GitHub il 5 novembre 2026:
[CI 39330380209](https://github.com/manueldellapa/SuperEnalotto-Analysis/actions/runs/39330380209)
su `56377a4`, evento push su `main` del 19 ottobre, conclusa con successo;
installazione bloccata, Ruff, mypy e pytest risultano tutti riusciti.
I collegamenti a codice/test nelle storie rendono ispezionabile la copertura,
senza sostituire l'esecuzione dei test. Il completamento M0 non attesta M1/M2.

Questa revisione valida documentazione e tracciabilità; non riesegue suite,
installazioni, smoke del comando installato o build e non produce una nuova
attestazione funzionale. Per modifiche future al codice
seguire anche l'aggiornamento Graphify richiesto dalle istruzioni del repository.

## Rischi e questioni aperte

| Rischio fondato | Impatto | Mitigazione e responsabilità |
| --- | --- | --- |
| Un download pulito ma ristretto sovrascrive il CSV; mancano attestazioni di copertura | Statistiche corrette sul campione possono sembrare storia completa | FR-005: mostrare date/N e copertura non certificata. US-002; nessuna nuova gestione della provenienza. |
| Una `Extraction` costruita dal CSV non si valida automaticamente | Conteggi ottenuti da input corrotto | Mitigazione M0 implementata: validazione esplicita dell'intero file e deduplicazione, US-001; preservarla prima dei filtri M1. |
| Identità annuale e SuperStar sovrapponibile sono dettagli già protetti dai test | Doppio conteggio o rigetto di record legittimi | Riusare regole e fixture, US-001/002; regressioni #28/#29. |
| Percentuali della sestina sommano a 600%, non a 100% | Interpretazione errata della metrica | Mitigazione M0 presente: `presence_percent`, denominatore N e descrizione nel report/README, US-002; preservare in M1/M2. |
| #30 è ancora aperta; il precedente limite del test packaging a un solo comando è risolto in M0 | La verifica degli entry point nel checkout non prova l'artefatto distribuito | TASK-004 completato per i due comandi; mantenere distinta la verifica automatizzata wheel/sdist, fuori da queste storie. |

Non risultano decisioni funzionali bloccanti con il perimetro proposto. Restano
da pianificare fuori da queste storie la versione di rilascio e l'eventuale
coordinamento con #30. Completezza storica certificata, export e ulteriori
metriche richiedono requisiti separati se richiesti in futuro.

## Validazione di questa revisione

Revisione documentale del 5 novembre 2026, secondo le skill `prd` e `graphify`:
controllati i cinque documenti, conservando 10 FR e 6 NFR canonici, 4 storie,
22 criteri AC e 8 task. Confrontati con la baseline i testi normativi,
identificativi, parent, dipendenze, fixture, collegamenti e heading esistenti.
Verificati unicità, riferimenti, copertura per incremento, dipendenze acicliche,
link locali e anchor, esiti numerici della fixture e coerenza con codice,
test, README e stati GitHub indicati sopra.

La struttura rimane composta dall'indice e dalle quattro storie: le milestone
restano qui per evitare duplicazioni. Graphify è stato usato per la navigazione;
filenames, heading preesistenti e collegamenti relativi restano stabili.
Il grafo generato non è rigenerato da questa revisione limitata ai PRD: le sue
posizioni di riga possono precederla e vanno confermate sui file attuali.
La documentazione resta leggibile senza Graphify.

Nessuna incoerenza documentale bloccante rilevata. Restano espliciti l'assenza
di issue dedicate e i limiti delle evidenze funzionali descritti sopra e in
US-002; non sono stati modificati codice, test, configurazioni o oggetti GitHub.
