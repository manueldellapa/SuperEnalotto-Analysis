# US-002 — Consultare frequenze e contesto del campione

[Indice e requisiti canonici](../README.md) · Milestone M0

Come utente del toolkit, voglio vedere quante volte compare ciascun numero
nel CSV disponibile e in quale quota delle estrazioni, distinguendo le categorie.

- Requisiti: FR-003, FR-004, FR-005, FR-007, FR-010 (comando base);
  NFR-001…006.
- Dipendenze: [US-001](US-001-lettura-validata.md).
- Impatto: nuovi `analysis.py` e `analysis_cli.py` proposti nel package,
  `pyproject.toml`, test speculari, `test_packaging.py` e README principale.
- Issue dedicata: assente. #6/#7 sono convenzioni già implementate; #30 resta
  separata, con collegamenti nell'indice.
- Definition of Ready: **READY**. Denominatore, categorie, vuoto e contratto CLI
  sono definiti. Inizio dopo US-001; nessuna dipendenza da servizi esterni.

## Fixture comune di riferimento

Dati sintetici, senza corrispondenza dichiarata con estrazioni reali. Riutilizzare
questa fixture nei test successivi, evitando di cambiare gli esiti attesi.

| Record | Data | Concorso | Sestina | Jolly | SuperStar |
| --- | --- | --- | --- | --- | --- |
| A | 2023-12-30 | 1 | 1, 2, 3, 4, 5, 6 | 7 | 1 |
| B | 2024-01-02 | 1 | 1, 2, 7, 8, 9, 10 | 3 | 3 |
| C | 2024-02-29 | 2 | 1, 11, 12, 13, 14, 15 | 2 | 1 |

Gli esiti seguenti si riferiscono ai tre record unici; aggiungere una copia di A
non deve cambiarli.

## Criteri di accettazione

| ID | Evidenza osservabile |
| --- | --- |
| AC-US-002-01 | Categoria `main`, senza filtri: N=3, 90 righe in ordine numerico. Il numero 1 ha conteggio 3 e presenza 100.00%; 2 ha 2 e 66.67%; 3 ha 1 e 33.33%; 90 ha 0 e 0.00%. Totale conteggi 18. Riordinare righe del CSV o posizioni della sestina non cambia il risultato. |
| AC-US-002-02 | Categoria `jolly`: 7, 3 e 2 hanno conteggio 1, tutti gli altri 0, totale 3. Categoria `superstar`: 1 ha 2, 3 ha 1, totale 3. Le coincidenze di SuperStar con sestina/Jolly non aggiungono presenze nelle altre categorie. |
| AC-US-002-03 | `superenalotto-analyze --data-dir <root>` seleziona `main`; opzioni di categoria producono gli esiti sopra. L'header mostra sorgente, nessun limite richiesto, date sorgente/selezionate 2023-12-30…2024-02-29 e N=3; testo esplicito su copertura non certificata e natura descrittiva. N non è il numero delle righe della tabella. |
| AC-US-002-04 | CSV con sola intestazione: successo, N=0, date sorgente/selezionate `N/A`, messaggio di selezione vuota di FR-007, 90 conteggi zero e percentuali `N/A`. Non produce `NaN`, percentuali numeriche o eccezioni. |
| AC-US-002-05 | Help restituisce 0; categoria sconosciuta o flag ignoto restituiscono 2. File assente, illeggibile, invalido o conflitto restituiscono 1 con diagnostica su stderr e stdout vuoto. Nessun errore atteso presenta traceback. |
| AC-US-002-06 | Entry point nuovo importabile e invocabile senza argomenti obbligatori Python; il comando installato esegue help e fixture. Downloader e launcher conservano target e comportamento, inclusa protezione del canonico. Nessun file dati è modificato, creato o cancellato; con canonico e parziale presenti si legge solo il primo. |
| AC-US-002-07 | I default della directory coincidono con `DataPaths.default()` sia da checkout sia da installazione; due radici esplicite nella stessa sessione producono risultati dai rispettivi CSV. L'output non contiene timestamp e rimane identico a parità di percorso, dati e opzioni. |

## Task atomici

### TASK-003 — Conteggi e percentuali puri

Parent: US-002. Dipendenze: TASK-002.

Introdurre il modulo puro di analisi e un contratto tipizzato minimo per 90
conteggi, categoria, N e contesto temporale. Ricevere estrazioni già validate e
deduplicate; separare il calcolo dalla formattazione. Riutilizzare costanti e
modello esistenti. La prima versione considera tutto il dataset e ordine
numerico, senza anticipare filtri o ranking.

Esito verificabile: AC-US-002-01/02/04 con test unitari, comprese invarianze di
ordine, duplicato eliminato dal lettore e somme delle percentuali non
arrotondate. Non riaprire il CSV per ogni numero o categoria.

### TASK-004 — Comando base, packaging e documentazione utente

Parent: US-002. Dipendenze: TASK-003.

Aggiungere parser/composizione/presentazione in `analysis_cli.py`, entry point
e gestione degli errori senza ampliare il downloader. Collegare il lettore
una sola volta, rendere visibili contesto e limiti dei dati, formattare due
decimali. Aggiornare il controllo esplicito dei due entry point in
`test_packaging.py`, con verifica di callable e default anche per il nuovo.
Aggiornare README con comando base, metriche, vuoto ed exit code.

Esito verificabile: AC-US-002-03…07 con `capsys`, `tmp_path` e monkeypatch,
test di packaging e suite downloader invariata. Risincronizzare l'ambiente
con `uv sync --locked --all-extras` per lo smoke dell'entry point installato.
Non aggiungere smoke wheel/sdist o workflow come parte di questo task.

## Approccio di verifica

Confrontare conteggi esatti e percentuali mostrate; usare tolleranza numerica
per invarianti su percentuali non arrotondate. Non esigere che le percentuali
arrotondate sommino esattamente a 600/100. Sostituire i confini HTTP con funzioni
che falliscono se chiamate e verificare file immutati. Per i default riusare
gli scenari di `tests/test_paths.py`. Eseguire i gate dell'indice per chiudere M0.
