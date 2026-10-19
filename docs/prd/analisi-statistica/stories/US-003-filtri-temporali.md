# US-003 — Analizzare un periodo scelto

[Indice e requisiti canonici](../README.md) · Milestone M1

Come utente, voglio limitare l'analisi a date precise per confrontare manualmente
campioni temporali con una definizione chiara degli estremi.

- Requisiti: FR-006, FR-007, FR-010 (filtri); preservare FR-002 e FR-005;
  NFR-002, NFR-003, NFR-006.
- Dipendenze: [US-002](US-002-frequenze.md); validazione completa di US-001.
- Impatto: `analysis.py`, `analysis_cli.py`, relativi test e README principale.
- Issue dedicata: assente; nessuna modifica a intervalli del downloader.
- Definition of Ready: **READY**. Semantica inclusiva, limiti mancanti, date
  esterne e vuoto definiti. Integrazione dopo M0; nessuna decisione bloccante.

## Criteri di accettazione

Usare la [fixture comune](US-002-frequenze.md#fixture-comune-di-riferimento).

| ID | Evidenza osservabile |
| --- | --- |
| AC-US-003-01 | Inizio 2024-01-02 e fine 2024-02-29 includono B e C: N=2, totale `main` 12; 1 ha 2 e 100.00%, 2 ha 1 e 50.00%. Le date sorgente restano quelle di A…C; le date selezionate sono quelle di B…C. |
| AC-US-003-02 | Limiti entrambi 2024-01-02 includono solo B. Solo inizio 2024-01-02 include B/C; solo fine 2024-01-02 include A/B. Nessun limite riproduce M0. I filtri funzionano identicamente per le tre categorie. |
| AC-US-003-03 | Intervallo 2023-12-01…2024-03-01 include A/B/C, riportando tali limiti richiesti e le date effettive diverse. Un intervallo senza record produce il report vuoto di FR-007 con N=0, date selezionate `N/A` e date sorgente ancora A…C. Un limite futuro è valido anche se non trova dati. |
| AC-US-003-04 | `2024-02-29` è accettata; `2023-02-29`, `2024-1-2`, `20240102`, un timestamp o inizio dopo fine sono errori di argomenti: exit 2, stderr esplicito, stdout vuoto. Non si applicano la soglia 2009, il mese corrente o la cascata del downloader. |
| AC-US-003-05 | Un record malformato o un conflitto fuori dall'intervallo selezionato provoca comunque exit 1 senza report. Una copia identica fuori/dentro il campione non aumenta N. Numero di concorso uguale fra anni diversi resta valido; il filtro usa la data completa. |

## Task atomici

### TASK-005 — Selezione temporale pura

Parent: US-003. Dipendenze: TASK-003.

Estendere il calcolo puro con limiti opzionali e inclusivi applicati alle
estrazioni già validate/deduplicate, mantenendo separati gli estremi della
sorgente e della selezione. Calcolare N e denominatori dopo la selezione.
Non introdurre orologio, calendario dei concorsi o righe sintetiche.

Esito verificabile: AC-US-003-01/02/03 e ordinamento temporale fra anni mediante
test unitari. Può essere preparato indipendentemente da TASK-004 e TASK-007;
non anticipare la loro integrazione CLI.

### TASK-006 — Filtri CLI e diagnostica

Parent: US-003. Dipendenze: TASK-004, TASK-005.

Esporre le due opzioni date, validarle e collegarle alla selezione. Mantenere
lettura/validazione dell'intera sorgente prima del filtro, senza riusare
`resolve_interval` o `validate_interval` del downloader. Aggiornare help e
README con esempi inclusivi, limiti singoli e vuoto.

Esito verificabile: AC-US-003-01…05 attraverso la CLI; test di mancata lettura
su argomenti invalidi, errore su record fuori intervallo e regressione M0.

## Approccio di verifica

Pytest parametrizzato per combinazioni di estremi e categorie; `capsys` e CSV
temporanei per la CLI. Verificare separatamente date richieste, date sorgente,
date selezionate e denominatore N. I test non richiedono freeze dell'orologio:
la funzionalità deve essere indipendente dalla data di esecuzione. Chiudere M1
con i gate esistenti descritti nell'indice.
