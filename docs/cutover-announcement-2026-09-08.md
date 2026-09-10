# Cutover announcement — 2026-09-08

Bilingual staff email for the FRM10-12 → SharePoint cutover. French first: the office is in
Montreal and the factory in Granby, and the shop-floor vocabulary is already French
(`Bobinage`, `Encuvage`, `Reçu`, `Entrepôt`).

Vocabulary matches `staff-guide-sharepoint-fr.md` deliberately: **la migration**, **copie en
lecture seule**, **c'est un miroir maintenant** — so this email and the guide read as one voice.

🔴 **One thing to fill in before sending: the link. Everything else is resolved** — see the
checklist at the bottom.

---

## FRANÇAIS

**Objet : FRM10-12 : la migration se fait ce soir. Voici ce qui change demain.**

Bonjour à tous,

**La migration se fait ce soir.** Quand vous arriverez demain matin, **SharePoint sera la
référence officielle** pour le suivi des unités.

**Ce qu'il faudra faire**

Faites vos mises à jour dans la liste **`Order Items`** dans SharePoint. La vue
**`FRM10-12 Layout`** vous présente les mêmes colonnes, dans le même ordre que dans le
classeur, donc vous devriez vous y retrouver tout de suite.

**Ce qu'il ne faudra plus faire**

**N'écrivez plus dans FRM10-12.** À partir de demain c'est un miroir : ce que vous y taperez
**ne sera pas transféré** et sera perdu.

**Si vous voulez seulement consulter le classeur**

**FRM10-12** reste consultable ici : **[LIEN]**
Il passe **en lecture seulement** : vous pourrez l'ouvrir et le lire, mais plus y écrire. Il se
reconstruit à partir de SharePoint à chaque rafraîchissement, donc **il date du dernier
rafraîchissement, pas de la minute**. Pour la donnée à jour à la seconde près, c'est SharePoint.

**Le guide complet** (comment saisir, comment lire les affichages) : **[LIEN GUIDE]**

**Ce qui change ce soir, et que vous allez voir**

Quelques colonnes cessent d'être une case où l'on tape une lettre et deviennent un vrai
contrôle. Même information, mais plus de convention à retenir :

- **Cases à cocher** : `Tank`, `ISO Stack`, `ISO Coil`, `Lead Assembly` (avant : `R`),
  `Temperature Rise`, `Impulse`, `Partial D`, `Oil Analysis`, `DB` (avant : `x`),
  `SFRA` (avant : `Y`).
- **Listes déroulantes** : `Order Type`, `Order Step`, `Order Status`, `Indexing`,
  `WET-WETP`, `Client Date Status`, `Core Type`, `Family`, `Model Type`, `Oil Type`,
  `Modification Status`, `New model to be created`. Les valeurs existantes restent
  affichées telles quelles; c'est seulement la saisie qui est encadrée.
- **`Status`** devient deux champs : **Step Status** (l'étape) et **Status Date** (la date).
- **Le dossier de la commande** apparaît directement sur l'unité : la colonne
  **Order - Order Folder** pointe vers l'endroit où vivent tous les documents de la
  commande.

**Les colonnes qui commencent par un préfixe**

Vous allez voir des colonnes nommées `Order - ...`, `Model - ...`, `Mod. Rev. - ...`,
`Client - ...`. Le préfixe dit d'où vient la valeur :

- **`Order -`** vient de la liste **Order** : ce qui concerne la commande au complet, le
  PO, la date promise, le type de commande.
- **`Model -`** vient de la liste **Models** : ce qui concerne le modèle.
- **`Mod. Rev. -`** vient de la liste **Model Revisions** : la spec technique, voltages,
  noyau, huile, kVA.
- **`Client -`** vient de la liste **Clients** : ce qui concerne le client.

Ce sont des **copies, tenues à jour automatiquement**. L'unité vous les montre pour que
vous n'ayez pas à aller les chercher ailleurs.

🔴 **N'écrivez pas dedans.** Ce que vous y tapez n'a pas l'air faux tout de suite : ça
reste affiché, l'air correct, jusqu'à ce que quelqu'un modifie cette commande ou ce
modèle, et là c'est remplacé sans avertissement. Si une de ces valeurs est fausse, ça se
corrige sur la commande, le modèle ou la révision. Venez me voir si vous n'êtes pas
certain lequel.

**Une question, un doute, quelque chose qui cloche ?**

Venez me voir tout de suite, sur Teams ou à **soleil.anker@ermco-eci.com**. Mieux vaut poser la
question deux minutes que de saisir au mauvais endroit toute la journée.

Merci à tous,
Soleil Anker-Baril

---

## ENGLISH

**Subject: FRM10-12: the migration happens tonight. Here is what changes tomorrow.**

Hello everyone,

**The migration happens tonight.** When you come in tomorrow morning, **SharePoint will be the
official record** for unit tracking.

**What to do from tomorrow**

Make your updates in the **`Order Items`** list in SharePoint. The **`FRM10-12 Layout`** view shows
the same columns, in the same order as the workbook, so it should look familiar straight
away.

**What to stop doing**

**Do not write in FRM10-12.** From tomorrow it is a mirror: anything you type into it **will not
be transferred** and will be lost.

**If you just want to look at the workbook**

**FRM10-12** is still there to look at: **[LINK]**
It becomes **read-only**: you can open it and read it, but not write to it. It rebuilds from
SharePoint each time it is refreshed, so **it is as current as the last refresh, not as current
as this minute**. For up-to-the-second data, go to SharePoint.

**The full guide** (how to enter data, how to read the views): **[GUIDE LINK]**

**What changes tonight, and what you will notice**

A few columns stop being a cell you type a letter into and become a proper control. Same
information, one less convention to remember:

- **Checkboxes**: `Tank`, `ISO Stack`, `ISO Coil`, `Lead Assembly` (was `R`),
  `Temperature Rise`, `Impulse`, `Partial D`, `Oil Analysis`, `DB` (was `x`),
  `SFRA` (was `Y`).
- **Dropdowns**: `Order Type`, `Order Step`, `Order Status`, `Indexing`, `WET-WETP`,
  `Client Date Status`, `Core Type`, `Family`, `Model Type`, `Oil Type`,
  `Modification Status`, `New model to be created`. Existing values keep showing exactly
  as they are; it is only new entry that is constrained.
- **`Status`** becomes two fields: **Step Status** (the step) and **Status Date** (the date).
- **The order's folder** now appears on the unit itself. The **Order - Order Folder**
  column points at where every document filed against that order lives.

**Columns that start with a prefix**

You will see columns named `Order - ...`, `Model - ...`, `Mod. Rev. - ...`,
`Client - ...`. The prefix tells you where the value comes from:

- **`Order -`** comes from the **Order** list: things about the whole order, the PO, the
  promised date, the order type.
- **`Model -`** comes from the **Models** list: things about the model.
- **`Mod. Rev. -`** comes from the **Model Revisions** list: the technical spec,
  voltages, core, oil, kVA.
- **`Client -`** comes from the **Clients** list: things about the client.

They are **copies, kept up to date automatically**. The unit shows them so you don't have
to go looking somewhere else.

🔴 **Don't type into them.** What you type does not look wrong straight away: it sits
there looking correct until somebody edits that order or model, and then it is replaced
without warning. If one of those values is wrong, it needs fixing on the order, the model
or the revision. Come and ask me if you are not sure which.

**Questions, doubts, anything that looks wrong?**

Come and find me straight away, on Teams or at **soleil.anker@ermco-eci.com**. Two minutes of
asking beats a whole day of entering things in the wrong place.

Thanks everyone,
Soleil Anker-Baril

---

## Before you send — checklist

**1. 🔴 Fill in `[LIEN]` / `[LINK]` and `[LIEN GUIDE]` / `[GUIDE LINK]`.** Two URLs, neither
invented here: the read-only workbook, and wherever `staff-handbook-sharepoint.md` /
`-fr.md` gets published (a SharePoint page on the site is the obvious home — staff are
already there, and it needs no separate permission).

**2. ✅ RESOLVED 2026-09-10 — it is a live copy, refreshed, not a frozen snapshot.** The viewer
rebuilds from SharePoint on every refresh, and someone owns running that refresh so FRM11 and
the reports stay fresh. So the "live copy" wording is the correct fork.

⚠️ But it is refreshed **on a schedule, by a person** — not continuously. The email now says
that outright ("as current as the last refresh, not as current as this minute"), because the
risk this checklist item was written about is real in a softer form: staff who believe the
workbook is live will read a stale figure off it and never think to check. Naming the limit
costs one clause and removes the whole failure mode.

**2b. ✅ TENSED FOR A SEND THIS EVENING, read tonight or tomorrow morning.**
It went through three revisions today; recording where it landed and why, so it does not
get moved a fourth time:

- Written originally as a post-cutover announcement — *"à compter de ce matin"*.
- Retensed to go out before the cutover **and** ask staff to save and close FRM10-12,
  because that is runbook step 4.
- The save-and-close was cut: by 19:00 everyone had already left, so it is an
  instruction nobody can act on — noise, and mildly alarming noise.
- Final: *"la migration se fait ce soir… quand vous arriverez demain matin"*. True when
  sent this evening **and** still true read over breakfast, which is the only tense that
  survives both.

It also says plainly that there is nothing to do tonight, so nobody feels summoned back.

⚠️ **What this costs, and it is not nothing:** nobody is told to save and close FRM10-12
before the freeze. Anything sitting unsaved on a machine tonight never reaches SharePoint.
Not fixable by email at this hour — but worth knowing now rather than discovering it in
the re-diff at step 9. If the re-diff turns up units that look stale, this is the first
thing to suspect.

**3. Optional line, if staff have been complaining about the dates.** The run fixed ~4,700 date
values that were displaying one day early. If that was visible to people, it is worth a sentence,
because it builds trust in the new list:

- FR: *« Au passage : les dates qui s'affichaient avec une journée de retard sont corrigées. »*
- EN: *"One more thing: the dates that were showing a day early are now corrected."*

**4. 🔴 Do not send this to whoever produces the supplier reports without warning them first.**
FRM11 reads FRM10-12's `TableOrders` as its root source — 890 rows feeding **8 supplier report
sheets to 8 outside companies**. Once staff stop maintaining the workbook, FRM11 goes **silently
stale**. Nobody should send a supplier report from FRM11 until it is repointed. FRM13 and FRM09
read the same table.

**5. Ask people to save and close FRM10-12 before they stop.** Anything sitting unsaved, or saved
after the final refresh, never reached SharePoint. Two units were only found this morning because
they were missing entirely — worth not adding more.

**6. ✅ DONE 2026-09-10 — the guides are consolidated and the banners are gone.**
`staff-handbook-sharepoint.md` and `-fr.md` merge the two guides staff would otherwise have to
read separately: Part 1 doing the work (from `staff-guide-*`), Part 2 the views (from
`views-guide-*`), one "something look wrong" section at the end. Text is the reviewed wording
verbatim — stitched, not rewritten — with the pre-publication banners stripped. **This is the
`[LIEN GUIDE]` target.**

⚠️ **One item still unverified inside it**, carried over from `views-guide-sharepoint-fr.md`:
section 7 of the French handbook names three UI labels — **« Regrouper par »**, **« Réduits »**,
**« Limite d'éléments »** — that were reasoned, never read off the screen. Open the classic
view-settings page in French and confirm. Thirty seconds, and it matters more than it looks:
staff search for those exact words, and a guide naming a button that does not exist makes them
doubt the parts that are right.

**Superseded, for reference —** the originals open with a
*"NE PAS DISTRIBUER — ce guide n'est pas encore vrai"* / do-not-distribute banner, written on
2026-09-04 because the cutover had been interrupted. It has now happened, so **the banner is
stale and the guides are true** — the two instructions the banner flags as backwards (*"N'écrivez
pas dedans"* and *"tout ce qui est tapé dedans va être effacé"*) are now exactly right. Strip the
banner and the guides can go out alongside this email.
