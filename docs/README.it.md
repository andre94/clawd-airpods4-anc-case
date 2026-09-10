# Clawd AirPods 4 ANC Case

Custodia protettiva esterna, in due parti, per il case di ricarica **AirPods 4
con ANC**. È un progetto fan-made ispirato a Clawd, non un prodotto Apple o
Anthropic e non un sostituto del case elettronico originale.

**v04 / v0.4.0-alpha: prototipo non ancora verificato fisicamente.** I controlli
digitali non garantiscono dimensioni finite, tenuta del coperchio, ricarica o
resistenza del foro. Non affidargli il trasporto degli AirPods prima delle prove.

## Link del progetto

Registro del **10 settembre 2026**: GitHub contiene i sorgenti v04 di riferimento;
le altre piattaforme restano v03 finché l'aggiornamento non viene verificato.

| Piattaforma | Link | Stato e contenuti |
| --- | --- | --- |
| GitHub | [Repository sorgenti](https://github.com/andre94/clawd-airpods4-anc-case) | Pubblico; CAD modificabile, script e documentazione di riferimento. |
| GitHub Releases | [Release e prerelease](https://github.com/andre94/clawd-airpods4-anc-case/releases) | Archivi sorgenti e file per la stampa versionati; v0.3.0-alpha conservata come storico. |
| Printables | [Pagina del modello](https://www.printables.com/model/1837773-clawd-airpods-4-anc-case-open-cad-v03-wip) | Pubblico v03; aggiornamento v04 in attesa. Due STL, 3MF, file Blender e rendering. |
| Sketchfab | [Visualizzatore 3D interattivo](https://sketchfab.com/3d-models/clawd-airpods-4-anc-case-open-cad-v03-wip-1aea2f19414b48d38c48bbdb90f80ad6) | Pubblico v03; aggiornamento v04 in attesa. Non è un file per la stampa. |
| Thingiverse | [Bozza salvata](https://www.thingiverse.com/thing:7407403) · [Editor del proprietario](https://www.thingiverse.com/thing:7407403/edit) | Bozza v03; aggiornamento v04 e visibilità pubblica non confermati. La pubblicazione iniziale era bloccata dall'attesa per i nuovi account. Login del proprietario richiesto. |

La pubblicazione non equivale a una verifica fisica. La pubblicazione su
Thingiverse non è programmata automaticamente: aggiornare questo stato datato
dopo l'effettiva messa online.

## Cosa scaricare

- Un corpo e un coperchio da `exports/clawd-v04/clawd-prototype/`.
- Scegliere i due STL **oppure** il 3MF contenente entrambi: non stampare duplicati.
- Unità millimetri, scala 100%. Il 3MF non contiene un profilo macchina validato.
- Il file Blender modificabile è in `models/`; parametri e script sono inclusi.

Corpo: circa **75,78 × 26,90 × 42,40 mm**; coperchio: **62 × 26,90 × 16,50 mm**.
Il foro portachiavi diagonale ha diametro nominale 4 mm. L'incisione
`andreabalbo.com` è profonda nominalmente 1 mm. Dispositivo e anello nei rendering
sono riferimenti visivi, non pezzi da stampare.

## Novità v04 e ritenzione

Maggiore copertura posteriore con scarico sagomato per la cerniera, finestra
frontale delimitata e aperture separate per USB-C e altoparlanti. Non è una
custodia sigillata o impermeabile. Sagoma, incisione e foro restano invariati.

Servono **cinque inserti morbidi separati**, non stampati: due sul corpo, due
ai lati del coperchio e uno nel tetto. Le sedi hanno un gioco normale nominale
di 0,65 mm. Schiuma di silicone morbida da 0,80 mm è solo uno spessore iniziale
da provare, non una specifica verificata. Senza inserti i gusci rigidi restano
privi di ritenzione. Se necessario, valutare un inserto biadesivo rimovibile nel
tetto, dopo aver verificato compatibilità e rimozione; niente colla permanente.

Il controllo digitale di 116 posizioni da 0 a 115° non rileva collisioni con il
simulacro e gli inserti illustrativi. **Non è una prova fisica di apertura senza
attrito né di tenuta.** [Dettagli v04](clawd-design-v04.md).

## Come procedere

Prima un prototipo non verniciato, poi eventuali correzioni e finitura colorata.
Far valutare al fornitore materiale, spessori, tolleranze finite e resistenza
dell'attacco. Il PA12 non caricato MJF/SLS è un candidato da valutare, non una
specifica già qualificata. FDM, resina e TPU non sono automaticamente equivalenti.

Verificare sul dispositivo reale inserimento, rimozione, ritenzione, apertura,
accesso USB-C, altoparlante, comandi e ricarica. Il foro sostiene soltanto il corpo
esterno: **non blocca il case AirPods né il coperchio della cover**. Per le prove
di trazione usare prima un guscio vuoto o un simulacro, non gli AirPods.

Guide: [stampa](PRINTING.md), [prove fisiche](QUALIFICATION.md),
[ricostruzione da sorgenti](BUILD.md), [contributi](../CONTRIBUTING.md).

## Licenze

CAD, parametri, documentazione e rendering originali/adattati: **CC BY-SA 4.0**.
Script e workflow: **MIT**. Gli asset originali di akmiller01 e Falah3D conservano
**CC BY 4.0**, con attribuzione. Le licenze ammettono anche riuso commerciale alle
loro condizioni, ma non attribuiscono diritti sui marchi né implicano approvazione
dei produttori. Leggere [licenze](../LICENSE.md) e
[crediti completi](../THIRD_PARTY_NOTICES.md).
