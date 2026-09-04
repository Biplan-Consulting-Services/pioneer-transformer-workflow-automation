# Les affichages SharePoint — comment ça marche

*Version anglaise : `views-guide-sharepoint.md`. Les deux ont la même structure, section par
section.*

> ### ⚠️ AVANT PUBLICATION — vérifier trois libellés d'interface (section 7)
> **À retirer une fois vérifié. Note interne, pas pour le personnel.**
>
> La section 7 nomme des éléments de la page de paramètres d'affichage en français :
> **« Regrouper par »**, **« Réduits »**, **« Limite d'éléments »**. Ces libellés ne sont **pas
> vérifiés** — je n'ai pas d'accès navigateur et je ne les ai donc pas lus dans l'interface. Ils
> viennent d'une supposition raisonnée, pas d'une lecture.
>
> **Pourquoi ça compte plus que d'habitude :** le personnel va chercher ces mots exacts dans
> l'écran. Un guide qui nomme un bouton qui n'existe pas est pire que pas de guide du tout — il
> fait douter du reste, y compris des parties justes.
>
> Le reste de la section 7 (le mécanisme, les 827 unités, le tri qui n'a aucun effet, la date
> vide qui compte comme la plus ancienne) est **vérifié** et ne dépend d'aucun libellé.
>
> À vérifier sur la page de paramètres de l'affichage classique, en français. Le deuxième réglage
> est déjà formulé de façon descriptive plutôt qu'en citation exacte, pour limiter le risque.

> **Où on en est aujourd'hui (2026-09-04).** On est en **fonctionnement parallèle** :
> **FRM10-12 reste actif et vous continuez de l'utiliser comme d'habitude.** Rien ne change dans
> votre travail quotidien pour l'instant. SharePoint se remplit en parallèle pour être prêt le
> jour où on basculera pour de bon. Ce guide vous explique comment lire ce qui est là — pas
> comment changer votre façon de travailler.

---

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

## 8. Quelque chose cloche ?

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
