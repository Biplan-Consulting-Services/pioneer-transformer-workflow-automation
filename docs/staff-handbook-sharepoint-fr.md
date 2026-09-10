# Order Items dans SharePoint — guide du personnel

Tout ce qu'il faut pour le suivi des unités au quotidien, maintenant que le suivi de
production sort de FRM10-12. Deux parties : **faire le travail**, puis **les affichages**
dans lesquels vous le faites.

Une question, quelque chose qui cloche, n'importe quoi — **Soleil Anker-Baril**, sur Teams
ou à soleil.anker@ermco-eci.com. Demander vaut toujours mieux que deviner.

---

# Partie 1 · Faire le travail

## Ce qui change

Le suivi de production sort du fichier Excel FRM10-12 et s'en vient dans SharePoint. Vous
mettez maintenant vos unités à jour directement dans une liste sur ce site, au lieu d'ouvrir
le classeur. Plus besoin d'attendre que quelqu'un d'autre ferme le fichier, et plus de
changements perdus.

Le fichier Excel existe encore, et il a exactement la même allure — mêmes colonnes, même
ordre, mêmes valeurs. C'est maintenant une **copie en lecture seule** qui se reconstruit
toute seule à partir de SharePoint. Consultez-le tant que vous voulez. Vos changements, eux,
se font dans SharePoint.

## Trouver votre travail

Ouvrez l'affichage (*view*) **Production Floor**.

Il montre seulement ce qui compte quand vous suivez une commande : le numéro d'unité, le
numéro de commande, où l'unité est rendue, qui la bobine, et quand elle est due. Tout le
reste est masqué.

Les unités sont **regroupées par Location** — l'étape de production : `Bobinage`, `Stacking`,
`Assemblage`, `Four`, `Tanking`, `Test`, `Finition`, `Livraison`, et les autres que vous
connaissez déjà. Toutes les unités rendues à la même étape apparaissent ensemble sous un même
titre, et vous pouvez replier un groupe qui ne vous concerne pas. Ça se lit comme un tableau
de production, pas comme un chiffrier.

Chaque Location a **sa propre couleur**, ce qui permet de voir d'un coup d'œil où l'ouvrage
s'accumule.

Dans chaque groupe, l'unité la plus pressante est en haut — trié par date due.

Seul l'ouvrage actif s'affiche. Les unités marquées livrées ou annulées disparaissent de
l'affichage toutes seules.

## Mettre une unité à jour

Cliquez dans la case. Écrivez. Passez à la suivante.

C'est tout. Il n'y a :

- **Aucun bouton d'enregistrement** — ça se sauvegarde à mesure
- **Aucun rafraîchissement à faire** — tout le monde voit votre changement immédiatement
- **Aucun « quelqu'un d'autre l'a ouvert »** — plusieurs personnes peuvent travailler en même
  temps

Si vous changez la Location d'une unité, elle saute d'elle-même dans son nouveau groupe.

## Ce qui a l'air différent

La plupart des colonnes fonctionnent comme avant. Quelques-unes ont maintenant un vrai
contrôle au lieu d'une case où vous tapiez une lettre — la même information, sauf que ce
n'est plus une convention à retenir.

| ce que vous tapiez avant | maintenant |
|---|---|
| `R` dans **Tank**, **ISO Stack**, **ISO Coil**, **Lead Assembly** | une **case à cocher** — cochez-la |
| `x` dans **Temperature Rise**, **Impulse**, **Partial D**, **Oil Analysis**, **DB** | une **case à cocher** — cochez-la |
| `Y` dans **SFRA** | une **case à cocher** — cochez-la |
| `Reçu` ou `Plaspak` dans **Frame** | une **liste déroulante** — choisissez |
| du texte libre dans **Order Type**, **Order Step**, **Order Status**, **Indexing**, **WET-WETP**, **Client Date Status**, **Core Type**, **Family**, **Model Type**, **Oil Type**, **Modification Status**, **New model to be created** | une **liste déroulante** — choisissez |
| un code comme `TE-Se-4` dans **Status** | deux champs : **Step Status** (choisir l'étape) et **Status Date** (choisir la date) |

Deux choses à savoir sur les cases à cocher :

- **Décochée veut dire « non ».** Il n'y a pas de troisième option pour « pas encore
  décidé » — si la nuance compte pour une unité, écrivez-la dans **Technical Notes** plutôt
  que de laisser la case décochée comme indice.
- **Une liste déroulante n'efface pas ce qui est déjà là.** Les valeurs saisies avant
  restent affichées telles quelles, même les orthographes bizarres. Ce que la liste
  encadre, c'est seulement ce que vous pouvez choisir à partir de maintenant — donc si
  une valeur dont vous avez besoin manque dans la liste, signalez-le plutôt que de
  contourner.
- **La copie Excel affiche encore les lettres.** Cochez la case Tank ici et le classeur en
  lecture seule montre `R`, exactement comme avant. Les rapports bâtis à partir de ce
  fichier ne changent pas.

## Si vous préférez l'ancienne disposition

Ouvrez plutôt l'affichage **Planning**. C'est la disposition **repliée** du classeur — les
mêmes colonnes, dans le même ordre, que celles que vous voyez dans FRM10-12 quand les
groupes de colonnes sont fermés. Si vous avez besoin d'une colonne de détail que vous
ouvririez normalement, elles sont toutes encore là dans l'affichage **All Items**.

## S.V.P., ne pas faire

**N'écrivez plus dans le fichier Excel.** C'est un miroir maintenant : il se reconstruit à
partir de SharePoint, donc tout ce qui est tapé dedans est effacé au prochain
rafraîchissement et ne se rend jamais dans SharePoint. Vous allez probablement voir que vous
ne pouvez plus écrire dedans du tout — il est mis en lecture seule — mais si jamais vous
êtes capable, c'est une erreur à signaler, pas une invitation.

**Ne travaillez pas autour d'un problème.** Voir plus bas.

---

# Partie 2 · Les affichages

## 1. Un affichage, c'est quoi ?

Dans SharePoint, il y a **une seule liste** d'unités. Tout le monde regarde les mêmes données.

Un **affichage** (*view*), c'est une **façon de regarder** cette liste : quelles colonnes on
montre, dans quel ordre, regroupées comment, triées comment, et lesquelles on cache.

L'image à retenir : la liste, c'est le classeur au complet. Un affichage, c'est une **paire de
lunettes**. Changer de lunettes ne change pas ce qui est écrit — juste ce que vous voyez.

**Ce qui découle de ça, et c'est le point important :**

- Changer d'affichage **ne modifie rien**. Vous ne pouvez pas briser des données en cliquant sur
  un affichage.
- Si vous modifiez une unité dans un affichage, **le changement est dans la liste**, donc tout le
  monde le voit, peu importe l'affichage qu'ils utilisent.
- Si une unité « disparaît » quand vous changez d'affichage, elle n'est **pas** effacée. Elle est
  juste filtrée par les lunettes que vous portez.

## 2. Changer d'affichage

En haut de la liste, il y a le **nom de l'affichage courant** avec une petite flèche à côté.
Cliquez dessus : la liste des affichages disponibles apparaît. Cliquez sur celui que vous voulez.

C'est tout. Pas de sauvegarde, pas de confirmation.

SharePoint **se souvient** du dernier affichage que vous avez ouvert. Si vous revenez demain et
que la liste n'a pas l'allure attendue, c'est probablement ça : vous êtes resté sur un autre
affichage. Rechangez-le, c'est tout.

## 3. Les affichages qui existent

Les quatre que vous utiliserez au quotidien :

| Affichage | Colonnes | À quoi il sert |
|---|---|---|
| **Production Floor** | 6 | L'affichage principal du plancher : où chaque unité est rendue. Regroupé par `Location`, avec une couleur par étape. Trié par date de livraison estimée. Seulement les unités actives. |
| **Planning** | 24 | La disposition **repliée** du classeur — les mêmes colonnes, dans le même ordre que dans FRM10-12 quand les groupes de colonnes sont fermés. Trié par date de livraison prévue. Seulement les unités actives. |
| **BO Tracking** | 23 | Le suivi des pièces en rupture (*back order*) : seulement les unités qui ont un BO, regroupées par BO, triées par date d'encuvage prévue. |
| **All Items** | 74 | Tout, sans filtre ni regroupement. C'est l'affichage par défaut, et le filet de sécurité — si une unité vous semble manquante ailleurs, elle est ici. |

### Vous allez en voir d'autres, et c'est normal

Dans le menu, il y a aussi des affichages que des collègues se sont créés — par exemple
**`Angelique reunion du lundi`**. Quelqu'un s'est déjà fait **sa propre copie de `Planning`**
pour sa réunion du lundi : partir d'un affichage existant, faire « Enregistrer l'affichage
sous », et lui donner un nom à soi.

**C'est exactement l'idée de la section 1.** Ces affichages-là ne sont **pas** des copies des
données — c'est la même liste, regardée avec d'autres lunettes. Ouvrir celui d'un collègue ne
dérange personne et ne change rien.

Et c'est justement là que vous pouvez ensuite ajuster : enlever des colonnes, changer le tri,
regrouper autrement — **dans votre copie**, sans toucher à l'affichage d'origine. Voir la
section 6.

## 4. Les regroupements

Dans **Production Floor**, les unités sont **regroupées par `Location`** — l'étape de production :
`Bobinage`, `Assemblage`, `Four`, `Finition`, `Livraison`, `Réparation`, `Entrepôt`, et les
autres que vous connaissez déjà.

- Toutes les unités rendues à la même étape apparaissent ensemble, sous un même titre.
- Le titre affiche le **nombre d'unités** dans le groupe. C'est votre charge de travail à cette
  étape, d'un coup d'œil.
- Cliquez sur la flèche du titre pour **replier** un groupe qui ne vous concerne pas. SharePoint
  s'en souvient.
- Si vous changez la `Location` d'une unité, elle **saute d'elle-même** dans son nouveau groupe.
  Vous n'avez rien d'autre à faire.

## 5. Trier et filtrer sans rien briser

Cliquez sur un **en-tête de colonne** : vous pouvez trier (A→Z, plus récent d'abord, etc.) ou
filtrer sur des valeurs précises.

**Ces changements-là ne sont que pour vous, et seulement pour le moment.** Ils ne modifient pas
l'affichage pour les autres et ils ne touchent pas aux données. Personne d'autre ne voit votre
tri.

Pour revenir à la normale : rouvrez l'affichage depuis le menu du haut, ou enlevez le filtre par
le même menu de colonne.

Un filtre actif est indiqué par une **petite icône d'entonnoir** dans l'en-tête. Si une liste a
l'air anormalement courte, **cherchez l'entonnoir** — c'est presque toujours l'explication.

## 6. Ce qu'il ne faut pas faire

**Ne modifiez pas un affichage partagé, et n'en supprimez pas.** Les quatre affichages ci-dessus
sont utilisés par tout le monde. Si vous changez les colonnes ou le tri de l'un d'eux, ça change
**pour toute l'usine**, pas juste pour vous.

Trier et filtrer par les en-têtes (section 5) est sans danger et n'est pas visé par cette
consigne. Ce qu'il faut éviter, c'est **Modifier l'affichage courant** et **Enregistrer
l'affichage**.

**Si vous voulez votre propre disposition, c'est tout à fait permis** — c'est comme ça que
`Angelique reunion du lundi` a été fait. Le seul piège, c'est qu'un affichage créé comme ça est
**public par défaut** : il apparaît dans le menu de tout le monde. Ce n'est pas grave, mais si
vous voulez qu'il reste à vous, ou si vous n'êtes pas sûr, **venez me voir** et on le crée
ensemble. C'est deux minutes.

## 7. Si votre affichage est regroupé et que des groupes ont l'air vides

**Rien n'a été effacé.** Les lignes sont encore là — c'est l'affichage qui a arrêté de charger
avant de les atteindre.

Ça arrive quand un groupe est beaucoup plus gros que tous les autres. Si la plupart des unités
n'ont pas de `Location`, ce groupe-là peut remplir l'affichage au complet à lui seul, et les plus
petits groupes se font pousser en dehors, là où vous ne les voyez pas. Ça a l'air exactement
comme des données disparues. Ça n'en est pas.

Et ce n'est pas un cas rare : **`Production Floor` regroupé par `Location` a 827 unités sans
Location.** N'importe quel regroupement où une valeur domine a la même allure.

Deux réglages l'évitent :

- Dans **Regrouper par** : mettre l'affichage des regroupements à **Réduits**. Un groupe réduit
  montre quand même son titre et son nombre, donc vous voyez tous les groupes et vous cliquez
  dans celui que vous voulez.
- Dans **Limite d'éléments** : choisir **d'afficher les éléments par lots**, et *non* de limiter
  le nombre total d'éléments retournés. Ce dernier fait arrêter l'affichage à la limite, sans
  aucun moyen de voir le reste.

Deux choses sur les regroupements qui surprennent à peu près tout le monde :

- **Si vous regroupez par une colonne, changer le tri de cette colonne dans la section Tri ne
  fait rien.** L'ordre des groupes se décide dans la section **Regrouper par**. Le mettre dans
  Tri a l'air de devoir marcher et n'a aucun effet.
- **Une date vide compte comme la date la plus ancienne.** Donc trier par une date met les
  unités non planifiées en haut, pas en bas. Si ce n'est pas ce que vous voulez, demandez — on
  vous fait un tri qui met les vides à la fin.

---

## Quelque chose cloche ?

**Venez voir Soleil Anker-Baril** — sur Teams, ou à soleil.anker@ermco-eci.com.

Avant de venir, ces trois réflexes règlent la grande majorité des cas :

1. **Vérifiez sur quel affichage vous êtes** (en haut de la liste). C'est la cause numéro un de
   « il manque des unités ».
2. **Cherchez une icône d'entonnoir** dans les en-têtes — un filtre laissé par accident.
3. **L'affichage est-il regroupé ?** Si oui, voir la section 7 — des groupes complets peuvent
   tomber en dehors de l'affichage sans que rien ne l'indique.

Si ce n'est aucun des trois : si une unité manque, si une colonne est vide alors qu'elle
devrait avoir une valeur, ou si quelque chose a l'air croche — **ne travaillez pas autour et ne
devinez pas.** Venez me voir. C'est un système neuf et trouver les défauts de jeunesse tout de
suite aide vraiment.
