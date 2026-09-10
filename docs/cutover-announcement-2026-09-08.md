# Cutover announcement — 2026-09-08

Bilingual staff email for the FRM10-12 → SharePoint cutover. French first: the office is in
Montreal and the factory in Granby, and the shop-floor vocabulary is already French
(`Bobinage`, `Encuvage`, `Reçu`, `Entrepôt`).

Vocabulary matches `staff-guide-sharepoint-fr.md` deliberately — **la bascule**, **copie en
lecture seule**, **c'est un miroir maintenant** — so this email and the guide read as one voice.

🔴 **One thing to fill in before sending: the link. Everything else is resolved** — see the
checklist at the bottom.

---

## FRANÇAIS

**Objet : FRM10-12 — la bascule est active. Ne plus y saisir de données.**

Bonjour à tous,

**À compter de ce matin, SharePoint devient la référence officielle** pour le suivi des unités.
La bascule est active.

**Ce qu'il faut faire maintenant**

Faites vos mises à jour dans la liste **`Order Items`** dans SharePoint. La vue
**`FRM10-12 Layout`** vous présente les mêmes colonnes, dans le même ordre que dans le classeur —
vous devriez vous y retrouver tout de suite.

**Ce qu'il ne faut plus faire**

**N'écrivez plus dans FRM10-12.** C'est un miroir maintenant. Ce que vous y taperez **ne sera pas
transféré** et sera perdu.

**Si vous voulez seulement consulter le classeur**

Utilisez la version **FRM10-12 — lecture seule** : **[LIEN]**
C'est une copie de consultation : on ne peut pas y écrire, et elle se reconstruit à partir de
SharePoint à chaque rafraîchissement — donc **elle date du dernier rafraîchissement, pas de la
minute**. Pour la donnée à jour à la seconde près, c'est SharePoint.

**Le guide complet** (comment saisir, comment lire les affichages) : **[LIEN GUIDE]**

**Une question, un doute, quelque chose qui cloche ?**

Venez me voir tout de suite — sur Teams, ou à **soleil.anker@ermco-eci.com**. Mieux vaut poser la
question deux minutes que de saisir au mauvais endroit toute la journée.

Merci à tous,
Soleil Anker-Baril

---

## ENGLISH

**Subject: FRM10-12 — the cutover is live. Please stop entering data in it.**

Hello everyone,

**As of this morning, SharePoint is the official record** for unit tracking. The cutover is live.

**What to do from now on**

Make your updates in the **`Order Items`** list in SharePoint. The **`FRM10-12 Layout`** view shows
the same columns, in the same order as the workbook — it should look familiar straight away.

**What to stop doing**

**Do not write in FRM10-12 any more.** It is a mirror now. Anything you type into it **will not be
transferred** and will be lost.

**If you just want to look at the workbook**

Use the **FRM10-12 — read-only** version: **[LINK]**
It is a reference copy: you cannot write to it, and it rebuilds from SharePoint each time it is
refreshed — so **it is as current as the last refresh, not as current as this minute**. For
up-to-the-second data, go to SharePoint.

**The full guide** (how to enter data, how to read the views): **[GUIDE LINK]**

**Questions, doubts, anything that looks wrong?**

Come and find me straight away — on Teams, or at **soleil.anker@ermco-eci.com**. Two minutes of
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
