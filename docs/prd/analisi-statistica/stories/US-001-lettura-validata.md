# US-001 — Leggere una sorgente statistica valida

[Indice e requisiti canonici](../README.md) · Milestone M0

Come utilizzatore dei dati scaricati, voglio che l'analisi ricostruisca i
concorsi dal CSV canonico senza includere record invalidi o duplicati.

- Requisiti: FR-001, FR-002; NFR-001, NFR-002, NFR-004, NFR-005, NFR-006.
- Dipendenze: nessuna nuova storia; riuso di `Extraction`, `validate_extraction`,
  `deduplicate_extractions`, `DataPaths` già presenti.
- Impatto: lettura in `pipeline.py`, test in `tests/test_pipeline.py`.
- Issue dedicata: assente. Contesto: #1, #7, #28 e #29, collegamenti nell'indice.
- Definition of Ready: **READY**. Formato, errori e regole di identità sono
  verificati; nessuna scelta bloccante. La storia abilita US-002, senza introdurre
  un comando utente incompleto.

## Criteri di accettazione

| ID | Evidenza osservabile |
| --- | --- |
| AC-US-001-01 | Un CSV scritto da `save_extractions_csv` e riletto restituisce le stesse `Extraction`; campi numerici restano interi e la data è una `date`. Una sorgente con righe riordinate viene restituita nell'ordine canonico della deduplicazione. |
| AC-US-001-02 | File vuoto, UTF-8 invalido, intestazione mancante/diversa/duplicata/riordinata, campo mancante/eccedente, data impossibile o non ISO stretta, intero `1.5`, `1e1`, `+1`, ` 1 `, cifre non ASCII o campo vuoto provocano errore senza risultati. Un file con sola intestazione restituisce una lista vuota. |
| AC-US-001-03 | Valore fuori 1–90, sestina ripetuta, concorso non positivo o Jolly nella sestina vengono rifiutati con percorso e riga. SuperStar uguale a un numero principale o al Jolly è accettato. |
| AC-US-001-04 | Duplicati identici contano una volta. Numero concorso uguale in due anni diversi produce due record. Stesso anno/numero con date o payload diversi provoca `ExtractionConflictError`, conservando il dettaglio del conflitto. |
| AC-US-001-05 | Sorgente assente o illeggibile genera errore distinguibile da una lista vuota; non viene usato il parziale anche se presente. Canonico, parziale e cache restano immutati; una radice assente non viene creata. |

## Task atomici

### TASK-001 — Parsing CSV verso il modello esistente

Parent: US-001. Dipendenze: nessuna.

Aggiungere in `pipeline.py` il lettore del formato canonico usando la libreria
standard, con percorso derivato da `DataPaths`. Controllare header, numero di
campi, sintassi stretta e conversione dei campi, mantenendo identificabile la
riga di errore. Non chiamare scraper né creare directory. Non aggiungere una
seconda definizione dell'header o un formato alternativo.

Esito verificabile: test round-trip e parametrizzati di AC-US-001-01/02,
lettura mancante/illeggibile di AC-US-001-05; nessuna scrittura. La gestione di
validazione semantica e deduplicazione viene completata da TASK-002.

### TASK-002 — Validazione e identità del dataset

Parent: US-001. Dipendenze: TASK-001.

Completare il lettore applicando i validatori a ogni record e la deduplicazione
esistente all'intera sorgente. Preservare gli errori di conflitto; associare
sorgente e riga agli errori di record. Documentare il contratto di uscita:
estrazioni valide, uniche e ordinate; nessun filtro applicato.

Esito verificabile: AC-US-001-03/04/05 e regressione dei test già esistenti su
deduplicazione, scrittura atomica e protezione del canonico. La story non cambia
le chiavi del parser HTML o il comportamento del downloader.

## Approccio di verifica

Usare `tmp_path`, `DataPaths.from_root`, `make_extraction` e
`save_extractions_csv`; costruire manualmente CSV invalidi quando il writer non
può rappresentarli. Simulare `OSError` con monkeypatch. Confrontare byte e lista
dei file prima/dopo, inclusi errori. Usare le convenzioni pytest del repository
e i gate descritti nell'indice. Non sono necessari download o fixture reali.
