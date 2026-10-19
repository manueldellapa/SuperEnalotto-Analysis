# US-004 — Ordinare i numeri per frequenza

[Indice e requisiti canonici](../README.md) · Milestone M2

Come utente, voglio consultare i numeri più e meno frequenti nel campione scelto,
con un limite di righe e un ordine prevedibile in caso di parità.

- Requisiti: FR-007, FR-008, FR-009, FR-010 (ordinamento/limite); preservare
  FR-004 e FR-005; NFR-002, NFR-003, NFR-005, NFR-006.
- Dipendenze: [US-003](US-003-filtri-temporali.md) per la consegna integrata;
  contratto dei conteggi di US-002 per il task puro.
- Impatto: `analysis.py`, `analysis_cli.py`, relativi test e README principale.
- Issue dedicata: assente.
- Definition of Ready: **READY**. Ordine, parità, limite, zeri e vuoto definiti;
  integrazione dopo M1, nessuna decisione bloccante.

## Criteri di accettazione

Usare la [fixture comune](US-002-frequenze.md#fixture-comune-di-riferimento).

| ID | Evidenza osservabile |
| --- | --- |
| AC-US-004-01 | `main`, intera sorgente, `--order most-frequent --top 3`: numeri 1, 2, 3 con conteggi 3, 2, 1 e posizioni 1, 2, 3. Le presenze sono 100.00%, 66.67%, 33.33% e N resta 3. Il limite esclude gli altri numeri anche se hanno lo stesso conteggio del numero 3. |
| AC-US-004-02 | `main`, `--order least-frequent --top 3`: numeri 16, 17, 18 con conteggio zero. Aumentando K si mantengono gli zeri in ordine numerico prima dei valori con presenze. Senza limite ogni classifica ha 90 righe; K=1 e K=90 sono validi. |
| AC-US-004-03 | Categoria `jolly`, ordine più frequenti e top 3: numeri 2, 3, 7, tutti con conteggio 1. Su B/C, `main`, più frequenti top 2 produce 1 e 2 con N=2. Cambiare ordine delle righe sorgente non cambia nessuna classifica. |
| AC-US-004-04 | Ordine numerico assente/esplicito riproduce M1; `--top` con tale ordine, K=0, K=91, K non intero e ordine sconosciuto producono exit 2 senza report. Entrambi gli ordini di frequenza supportano tutte le categorie e i filtri temporali. |
| AC-US-004-05 | Con N=0, classifica con o senza limite: successo, metadati e messaggio di assenza dati, nessuna riga classificata né numeri presentati come più/meno frequenti. Con N>0 i numeri mai presenti hanno invece conteggio e percentuale zero e possono apparire regolarmente. |

## Task atomici

### TASK-007 — Ordinamento deterministico dei risultati

Parent: US-004. Dipendenze: TASK-003.

Ordinare le 90 frequenze già calcolate, nei due versi richiesti, con spareggio
sul numero crescente; applicare K dopo l'ordinamento. Conservare contesto e
denominatore; distinguere N=0 da numeri con conteggio zero in un campione non
vuoto. Non aggiungere calcoli statistici o rilettura del CSV.

Esito verificabile: logica pura di AC-US-004-01/02/03/05. Preparabile
indipendentemente da TASK-004 e TASK-005 dopo stabilizzazione di TASK-003.

### TASK-008 — Classifiche CLI e documentazione finale

Parent: US-004. Dipendenze: TASK-006, TASK-007.

Esporre ordine e limite, validarne la combinazione e mostrare le posizioni
ordinali nelle sole classifiche. Aggiornare help e README con parità, inclusione
degli zeri, denominatore, limiti e vuoto; preservare le avvertenze descrittive
e di copertura. Integrare i test senza toccare il downloader o i workflow.

Esito verificabile: AC-US-004-01…05 attraverso la CLI, regressioni M0/M1 e smoke
del comando installato con dataset temporaneo. Nessuna esportazione di report.

## Approccio di verifica

Usare fixture con parità sia sopra sia sul confine K; confrontare numero,
conteggio, posizione e N. Per percentuali non confondere arrotondamento con
criterio di ordinamento: confrontare la classifica con i conteggi interi del
report completo. Testare limiti estremi e righe vuote, poi eseguire i gate
esistenti dell'indice per chiudere M2.
