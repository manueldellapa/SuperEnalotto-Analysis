# PRD — Analisi statistica delle estrazioni storiche

Stato: proposta pronta per implementazione incrementale. Revisione: 19 ottobre
2026. Baseline locale: commit `cd4bc39`, package `0.2.0`. Questo PRD descrive
comportamenti futuri; nessun comando di analisi è attualmente disponibile.

## Problema, utenti e risultato atteso

Chi usa il downloader dispone di un CSV validato, ma deve scrivere strumenti
propri per contare le uscite dei numeri, confrontarle e restringere il periodo.
La funzionalità serve a utenti del toolkit da terminale e sviluppatori Python
che vogliono esplorare i dati già scaricati.

Risultato: analisi descrittiva locale, ripetibile e verificabile, con frequenze
assolute, percentuali di presenza e classifiche. Ogni risultato rende evidente
quali estrazioni sono state considerate. Le frequenze storiche non devono
essere presentate come previsioni delle estrazioni successive.

## Evidenze del repository

L'analisi è partita dal grafo Graphify esistente, poi ha verificato le fonti e
i test pertinenti. Il grafo orienta la navigazione; i fatti sotto derivano dai
file attuali. Non esistono PRD, ADR o una struttura `docs/` preesistente nel
checkout esaminato.

| Fatto verificato | Fonte canonica o evidenza |
| --- | --- |
| Il prodotto acquisisce dati e produce CSV; non offre analisi statistiche | [README](../../../README.md), [package e dipendenze](../../../pyproject.toml) |
| `Extraction` è frozen/slotted e definisce le dieci colonne CSV | [models.py](../../../src/superenalotto/models.py) |
| I validatori controllano valori, unicità della sestina e Jolly; costruire `Extraction` da solo non valida | [validators.py](../../../src/superenalotto/validators.py), [test](../../../tests/test_validators.py) |
| L'identità è `(extraction_date.year, contest_number)`; duplicati uguali collassano, conflitti interrompono | `deduplicate_extractions` in [pipeline.py](../../../src/superenalotto/pipeline.py), [test](../../../tests/test_pipeline.py) |
| `DataPaths` deriva i percorsi dalla radice scelta; il default distingue checkout e installazione | [paths.py](../../../src/superenalotto/paths.py), [test](../../../tests/test_paths.py) |
| Il CSV canonico è una sovrascrittura dell'intervallo scaricato; i fallimenti producono un CSV parziale distinto | README, [cli.py](../../../src/superenalotto/cli.py), [test](../../../tests/test_cli.py) |
| Manca un lettore CSV che ricostruisca e validi le estrazioni; `count_csv_rows` conta soltanto righe | pipeline.py |
| Python supportato: 3.14.x; CLI con `argparse`; pytest, monkeypatch e `tmp_path`, senza HTTP reale | pyproject.toml, [supporto test](../../../tests/support.py) |
| CI esegue Ruff, mypy strict e pytest da dipendenze bloccate | [ci.yml](../../../.github/workflows/ci.yml) |

### Issue correlate

Ricerca GitHub in sola lettura il 19 ottobre 2026, query
`repo:manueldellapa/SuperEnalotto-Analysis is:issue`: 15 issue restituite, nessuna
dedicata a frequenze, filtri o classifiche. Stati delle issue sotto verificati
individualmente. Le nuove storie non hanno ancora issue associate; non crearle
automaticamente.

| Issue | Stato verificato | Relazione con il PRD |
| --- | --- | --- |
| [#1 — preservare il CSV canonico](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/1) | Chiusa | US-001 e US-002 devono preservarne le garanzie |
| [#6 — CLI installabile](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/6) | Chiusa | Convenzione riusata da US-002 |
| [#7 — directory configurabili](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/7) | Chiusa | `DataPaths` riusato da US-001 e US-002 |
| [#28 — identità per anno e concorso](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/28) | Chiusa | Regola da riusare in US-001, anche oltre il cambio d'anno |
| [#29 — Jolly distinto dalla sestina](https://github.com/manueldellapa/SuperEnalotto-Analysis/issues/29) | Chiusa | Validazione da riusare in US-001; SuperStar può coincidere |
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

Queste sono scelte del PRD, non capacità già presenti né preferenze confermate
dall'utente. Sono sufficientemente definite per l'implementazione e modificabili
in una successiva revisione mantenendo gli identificatori.

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

| Componente attuale | Impatto previsto |
| --- | --- |
| `pipeline.py` | Aggiungere la lettura CSV validata vicino all'I/O esistente; riusare validazione e deduplicazione, senza rifattorizzare il download. Il lettore restituisce dati prima del calcolo e non applica filtri. |
| `models.py`, `validators.py`, `constants.py` | Riutilizzare `Extraction`, header e regole 1–90; nessuna migrazione o modifica dell'entità. |
| `paths.py` | Riutilizzare `DataPaths.extractions_csv`, senza percorsi globali o nuove cartelle dati. |
| Nuovo `analysis.py` proposto | Calcolo puro di frequenze, selezione temporale e ordinamento; nessun disco/rete. Risultati con un semplice contratto tipizzato; evitare gerarchie di servizi e protocolli generici. Le funzioni di calcolo ricevono estrazioni già validate e deduplicate, precondizione da documentare. |
| Nuovo `analysis_cli.py` proposto | Parsing, risoluzione dei percorsi, composizione lettura/calcolo, formattazione e codici d'uscita. Non ampliare il parser del downloader. |
| `pyproject.toml`, `tests/test_packaging.py` | Aggiungere entry point. Il test attuale confronta l'intera mappa con un solo comando: aggiornarlo per verificare precisamente entrambi e la chiamabilità, senza cancellare la garanzia precedente. |
| Test e README | Estendere `test_pipeline.py` e `test_packaging.py`; aggiungere test speculari ai due moduli nuovi. Documentare uso e confini del report nel README durante l'implementazione. |

Non serve database, schema nuovo, servizio esterno o migrazione. Il lettore è
stretto sul formato oggi scritto dal progetto; l'eventuale supporto a CSV di
terze parti richiederà un requisito successivo esplicito. Il nuovo comando non
deve alterare CLI, launcher, uscite o protezione del CSV parziale del downloader.

### Interfaccia finale proposta

Esempi futuri, disponibili solo dopo le milestone corrispondenti:

```bash
# M0: frequenze di tutta la sorgente disponibile, numeri principali
superenalotto-analyze --data-dir ~/superenalotto-data

# M1: periodo inclusivo e categoria separata
superenalotto-analyze --data-dir ~/superenalotto-data --category jolly \
  --start-date 2024-01-01 --end-date 2024-12-31

# M2: primi dieci per frequenza nel periodo, oppure meno frequenti
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

| ID | Risultato e criterio di uscita | Dipendenze | Storie e requisiti |
| --- | --- | --- | --- |
| M0 | Frequenze utilizzabili da CLI sull'intero CSV: ingresso validato, 90 numeri, categorie separate, percentuali e metadati verificati; gate verdi. US-001 è il prerequisito tecnico minimo incluso nello stesso incremento verticale di US-002. | Nessuna nuova dipendenza esterna | [US-001](stories/US-001-lettura-validata.md), [US-002](stories/US-002-frequenze.md); FR-001…005, FR-007, FR-010 (comando base); NFR-001…006 |
| M1 | Stesso report limitabile per data, con estremi e assenza di risultati corretti; nessuna regressione M0; gate verdi. | M0 | [US-003](stories/US-003-filtri-temporali.md); FR-006/007/010 (filtri), NFR-002/003/006 |
| M2 | Classifiche complete o top K, più/meno frequenti, parità e zeri deterministici anche con filtri; gate verdi. | M1 | [US-004](stories/US-004-classifiche.md); FR-007…010 (ordinamento/limite), NFR-002/003/005/006 |

Ordine delle storie: US-001 → US-002 → US-003 → US-004. I task puri sui filtri e
sulle classifiche possono essere preparati indipendentemente dopo il contratto
di conteggio di TASK-003; integrazione CLI e consegna seguono le milestone.

| Storia | Task atomici | Dipendenza di storia | Definition of Ready | Issue dedicata |
| --- | --- | --- | --- | --- |
| US-001 | TASK-001, TASK-002 | Nessuna | READY | Assente |
| US-002 | TASK-003, TASK-004 | US-001 | READY | Assente |
| US-003 | TASK-005, TASK-006 | US-002 | READY | Assente |
| US-004 | TASK-007, TASK-008 | US-003 | READY | Assente |

READY significa che non manca una decisione per iniziare la storia quando i
prerequisiti sono consegnati; non significa che i predecessori siano già
implementati. I dettagli di criteri AC e verifiche risiedono nelle storie.

## Verifica e successo misurabile

Il completamento richiede tutti i criteri AC delle quattro storie soddisfatti,
copertura di ogni FR nella tabella sopra e test su fixture con risultati noti:
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
locale aggiuntiva, senza descriverlo come gate CI. Quando si aggiunge il comando,
risincronizzare l'ambiente e verificarne `--help` e una fixture temporanea tramite
l'entry point installato. La verifica di wheel/sdist resta distinta (#30).

Questo lavoro di pianificazione valida documentazione e tracciabilità; non
esegue né attesta questi gate di implementazione. Per modifiche future al codice
seguire anche l'aggiornamento Graphify richiesto dalle istruzioni del repository.

## Rischi e questioni aperte

| Rischio fondato | Impatto | Mitigazione e responsabilità |
| --- | --- | --- |
| Un download pulito ma ristretto sovrascrive il CSV; mancano attestazioni di copertura | Statistiche corrette sul campione possono sembrare storia completa | FR-005: mostrare date/N e copertura non certificata. US-002; nessuna nuova gestione della provenienza. |
| Una `Extraction` costruita dal CSV non si valida automaticamente | Conteggi ottenuti da input corrotto | Validazione esplicita dell'intero file e deduplicazione prima dei filtri, US-001. |
| Identità annuale e SuperStar sovrapponibile sono dettagli già protetti dai test | Doppio conteggio o rigetto di record legittimi | Riusare regole e fixture, US-001/002; regressioni #28/#29. |
| Percentuali della sestina sommano a 600%, non a 100% | Interpretazione errata della metrica | Nome `presence_percent`, denominatore N e descrizione nel report/README, US-002. |
| Il test packaging attuale ammette un solo comando; #30 è ancora aperta | Fallimento prevedibile del test o affidabilità dell'artefatto non provata | Aggiornamento mirato in TASK-004; distinguere test del checkout da smoke dell'artefatto. |

Non risultano decisioni funzionali bloccanti con il perimetro proposto. Restano
da pianificare fuori da queste storie la versione di rilascio e l'eventuale
coordinamento con #30. Completezza storica certificata, export e ulteriori
metriche richiedono requisiti separati se richiesti in futuro.

## Validazione di questa revisione

Controllati i cinque documenti: 10 FR e 6 NFR canonici, 4 storie con stato e
dipendenze espliciti, 22 criteri AC univoci e 8 task con parent e dipendenze
acicliche. Verificati i link locali e gli anchor, la copertura dei requisiti
nelle storie, l'ordine delle milestone e gli esiti numerici della fixture.
Rivisti i riferimenti alle fonti e alle issue sopra; nessuna incoerenza bloccante
rilevata. Queste verifiche riguardano il PRD, non l'esecuzione della funzionalità
futura o il superamento della suite del progetto.
