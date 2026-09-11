# Order Items dans SharePoint : guide du personnel

**Fini d'attendre que quelqu'un d'autre ferme le fichier. Fini les changements qui
disparaissent.**

FRM10-12 sort d'Excel et s'en va dans SharePoint. Vos unités sont maintenant dans une
liste qui s'appelle **Order Items**, où plusieurs personnes peuvent travailler en même
temps, où chaque changement s'enregistre à mesure que vous tapez, et où rien ne se
perd parce que deux personnes avaient le fichier ouvert.

Vous pouvez aussi arrêter de chercher à travers des colonnes que vous n'utilisez
jamais. La liste s'ouvre dans la disposition que vous connaissez déjà, et à partir de
là vous pouvez vous bâtir un affichage qui montre seulement ce avec quoi vous
travaillez.

La **partie 1**, c'est comment mettre une unité à jour. La **partie 2**, c'est comment
fonctionnent les affichages.

Si vous avez des questions ou si vous voyez quelque chose d'anormal, vous pouvez
contacter **Soleil Anker-Baril** sur Teams ou à soleil.anker@ermco-eci.com.
Demander vaut toujours mieux que deviner.

---

# Partie 1 · Faire le travail

## Ce qui arrive au fichier Excel

Il est encore là, et il a exactement la même allure : mêmes colonnes, même ordre, mêmes
valeurs. C'est maintenant une **copie en lecture seule** qui se reconstruit toute seule à
partir de SharePoint, alors consultez-le tant que vous voulez. Ce que vous changez, ça se
fait dans SharePoint.

## Trouver votre travail

Ouvrez l'affichage **`FRM10-12 Layout`**. C'est la disposition du classeur : les mêmes
colonnes, dans le même ordre que vous avez l'habitude, donc vous devriez vous y retrouver
tout de suite. Commencez par là.

**Ensuite, faites-vous en un à vous.** `FRM10-12 Layout` contient tout, ce qui veut dire
qu'il contient aussi beaucoup de choses que vous, personnellement, ne regardez jamais. Vous
pouvez vous bâtir un affichage avec seulement les colonnes dont vous avez besoin, trié et
regroupé comme vous pensez le travail, et il sera là chaque fois que vous ouvrez la liste.

🔑 **Venez le faire avec moi la première fois.** Ça prend deux minutes, et il y a un
réglage qui vaut la peine d'être bien mis dès le départ : un affichage que vous créez est
**public par défaut**, donc il apparaît dans le menu de tout le monde. Ce n'est pas un
drame, mais c'est plus simple à décider au départ qu'à démêler après. Après le premier,
vous n'aurez plus besoin de moi.

**Les autres affichages**

Les trois affichages FRM10-12 ont les mêmes colonnes, dans le même ordre. Seul le filtre
change :

| affichage | montre |
|---|---|
| **`FRM10-12 Layout`** | l'ouvrage actif : tout ce qui n'est pas encore livré |
| **`FRM10-12 Completed`** | les unités livrées |
| **`FRM10-12 All`** | tout, livré ou non |

**`FRM10-12 All`**, c'est celui à vérifier quand une unité a l'air d'avoir disparu. Neuf
fois sur dix elle a simplement été livrée et est sortie de `FRM10-12 Layout`.

**`BO Tracking`** montre seulement les unités qui ont un back order.

Vous verrez aussi des affichages que des collègues se sont bâtis. En ouvrir un ne change
rien pour eux, alors regardez si ça vous sert. C'est la même liste de toute façon.

## Mettre une unité à jour

Cliquez dans la case. Écrivez. Passez à la suivante.

C'est tout. Il n'y a :

- **Aucun bouton d'enregistrement** : ça se sauvegarde à mesure
- **Aucun rafraîchissement à faire** : tout le monde voit votre changement immédiatement
- **Aucun « quelqu'un d'autre l'a ouvert »** : plusieurs personnes peuvent travailler en même
  temps

Si vous changez la Location d'une unité, elle saute d'elle-même dans son nouveau groupe.

## Ce qui a l'air différent

La plupart des colonnes fonctionnent comme avant. Quelques-unes ont maintenant un vrai
contrôle au lieu d'une case où vous tapiez une lettre, la même information, sauf que ce
n'est plus une convention à retenir.

| ce que vous tapiez avant | maintenant |
|---|---|
| `R` dans **Tank**, **ISO Stack**, **ISO Coil**, **Lead Assembly** | une **case à cocher**, cochez-la |
| `x` dans **Temperature Rise**, **Impulse**, **Partial D**, **Oil Analysis**, **DB** | une **case à cocher**, cochez-la |
| `Y` dans **SFRA** | une **case à cocher**, cochez-la |
| `Reçu` ou `Plaspak` dans **Frame** | une **liste déroulante**, choisissez |
| du texte libre dans **Order Type**, **Order Step**, **Order Status**, **Indexing**, **WET-WETP**, **Client Date Status**, **Core Type**, **Family**, **Model Type**, **Oil Type**, **Modification Status**, **New model to be created** | une **liste déroulante**, choisissez |
| un code comme `TE-Se-4` dans **Status** | deux champs : **Step Status** (choisir l'étape) et **Status Date** (choisir la date) |

Deux choses à savoir sur les cases à cocher :

- **Décochée veut dire « non ».** Il n'y a pas de troisième option pour « pas encore décidé ». Si la nuance compte pour une unité, écrivez-la dans **Technical Notes** plutôt
  que de laisser la case décochée comme indice.
- **Une liste déroulante n'efface pas ce qui est déjà là.** Les valeurs saisies avant
  restent affichées telles quelles, même les orthographes bizarres. Ce que la liste
  encadre, c'est seulement ce que vous pouvez choisir à partir de maintenant. Donc si une valeur dont vous avez besoin manque dans la liste, signalez-le plutôt que de
  contourner.
- **La copie Excel affiche encore les lettres.** Cochez la case Tank ici et le classeur en
  lecture seule montre `R`, exactement comme avant. Les rapports bâtis à partir de ce
  fichier ne changent pas.
- **Si une colonne ne fonctionne pas comme votre travail l'exige, venez me le dire.** Ces
  choix ont été faits colonne par colonne, à partir de la façon dont le classeur était
  utilisé, et certains vont s'avérer mauvais pour du travail que je n'ai pas vu. Une case
  à cocher qui aurait besoin d'un troisième état, une liste déroulante à laquelle il
  manque une option, un champ qui devrait accepter du texte libre : tout ça peut être
  changé. C'est un réglage, pas une reconstruction. **Ne contournez pas le problème** en
  mettant la vraie réponse ailleurs, parce qu'à ce moment-là personne ne sait que la
  colonne est fausse.

## Les colonnes qui viennent d'ailleurs

Certains noms de colonnes commencent par un préfixe. Le préfixe vous dit de quelle liste
la valeur provient :

| préfixe | provient de | ce qu'on y trouve |
|---|---|---|
| **Order -** | la liste **Order** | ce qui concerne la commande au complet : le PO, la date promise, le type de commande, les notes de vente |
| **Model -** | la liste **Models** | ce qui concerne le modèle, commun à toutes les unités bâties dessus |
| **Mod. Rev. -** | la liste **Model Revisions** | la spec technique : voltages, type de noyau, huile, kVA, la révision du dessin |
| **Client -** | la liste **Clients** | ce qui concerne le client, par exemple son délai |

Il y en a 48. La plupart sont masquées dans les affichages où vous travaillez au quotidien; vous ne
voyez l'ensemble que si vous allez le chercher.

Ce sont des **copies, tenues à jour automatiquement**. L'unité vous les montre pour que
vous puissiez voir le PO d'une commande ou le voltage d'un modèle sans ouvrir une autre
liste, mais la vraie valeur vit sur l'autre liste.

**N'écrivez pas dans ces colonnes.** Ce n'est pas la source de la donnée. Toute valeur
saisie ici sera remplacée par celle de la liste d'origine dès que cette liste sera
modifiée. Pour corriger une de ces valeurs, il faut le faire sur la commande, sur le modèle
ou sur la révision. Venez me voir si vous ne savez pas laquelle.

## S.V.P., ne pas faire

**N'écrivez plus dans le fichier Excel.** C'est un miroir maintenant : il se reconstruit à
partir de SharePoint, donc tout ce qui est tapé dedans est effacé au prochain
rafraîchissement et ne se rend jamais dans SharePoint. Vous allez probablement voir que vous
ne pouvez plus écrire dedans du tout, il est mis en lecture seule, mais si jamais vous
êtes capable, c'est une erreur à signaler, pas une invitation.

**Ne travaillez pas autour d'un problème.** Voir plus bas.

---

# Partie 2 · Les affichages

## 1. Un affichage, c'est quoi ?

Dans SharePoint, il y a **une seule liste** d'unités. Tout le monde regarde les mêmes données.

Un **affichage** (*view*), c'est une **façon de regarder** cette liste : quelles colonnes on
montre, dans quel ordre, regroupées comment, triées comment, et lesquelles on cache.

L'image à retenir : la liste, c'est le classeur au complet. Un affichage, c'est une **paire de
lunettes**. Changer de lunettes ne change pas ce qui est écrit, juste ce que vous voyez.

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
| **FRM10-12 Layout** | 24 | **Commencez ici.** La disposition du classeur : les mêmes colonnes, dans le même ordre que vous avez l'habitude. Trié par date de livraison prévue. Unités actives seulement. |
| **BO Tracking** | 23 | Le suivi des pièces en rupture (*back order*) : seulement les unités qui ont un BO, regroupées par BO, triées par date d'encuvage prévue. |
| **FRM10-12 Completed** | 24 | Mêmes colonnes, unités livrées seulement. |
| **FRM10-12 All** | 24 | Mêmes colonnes, sans filtre. **À vérifier en premier quand une unité semble manquer.** |
| **BO Tracking** | 23 | Suivi des back orders : seulement les unités qui ont un BO, regroupé par BO, trié par date d'encuvage prévue. |

### Vous allez en voir d'autres, et c'est normal

Dans le menu, il y a aussi des affichages que des collègues se sont bâtis. C'est exactement
comme ça que c'est censé marcher : partir d'un affichage existant, faire « Enregistrer
l'affichage sous », et lui donner un nom à soi.

**C'est exactement l'idée de la section 1.** Ces affichages-là ne sont **pas** des copies des
données, c'est la même liste, regardée avec d'autres lunettes. Ouvrir celui d'un collègue ne
dérange personne et ne change rien.

Et c'est justement là que vous pouvez ensuite ajuster : enlever des colonnes, changer le tri,
regrouper autrement, **dans votre copie**, sans toucher à l'affichage d'origine. Voir la
section 6.

## 4. Les regroupements

Quand un affichage est **regroupé par `Location`**, c'est-à-dire : l'étape de production :
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
l'air anormalement courte, **cherchez l'entonnoir**, c'est presque toujours l'explication.

## 6. Ce qu'il ne faut pas faire

**Ne modifiez pas un affichage partagé, et n'en supprimez pas.** Les quatre affichages ci-dessus
sont utilisés par tout le monde. Si vous changez les colonnes ou le tri de l'un d'eux, ça change
**pour toute l'usine**, pas juste pour vous.

Trier et filtrer par les en-têtes (section 5) est sans danger et n'est pas visé par cette
consigne. Ce qu'il faut éviter, c'est **Modifier l'affichage courant** et **Enregistrer
l'affichage**.

**Un affichage à vous, c'est le but, pas l'exception**, c'est comme ça que ceux déjà dans le
menu ont été faits. Le seul piège, c'est qu'un affichage créé comme ça est **public par
défaut** : il apparaît dans le menu de tout le monde. Ce n'est pas grave, mais si vous voulez
qu'il reste à vous, ou si vous n'êtes pas sûr, **venez me voir et on fait le premier
ensemble.** C'est deux minutes, et après vous n'aurez plus besoin de moi.

## 7. Si votre affichage est regroupé et que des groupes ont l'air vides

**Rien n'a été effacé.** Les lignes sont encore là, c'est l'affichage qui a arrêté de charger
avant de les atteindre.

Ça arrive quand un groupe est beaucoup plus gros que tous les autres. Si la plupart des unités
n'ont pas de `Location`, ce groupe-là peut remplir l'affichage au complet à lui seul, et les plus
petits groupes se font pousser en dehors, là où vous ne les voyez pas. Ça a l'air exactement
comme des données disparues. Ça n'en est pas.

Et ce n'est pas un cas rare : **regrouper `Order Items` par `Location` met 827 unités sous une seule
rubrique « sans Location ».** N'importe quel regroupement où une valeur domine a la même allure.

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
  unités non planifiées en haut, pas en bas. Si ce n'est pas ce que vous voulez, demandez, on
  vous fait un tri qui met les vides à la fin.

---

## Quelque chose cloche ?

**Venez voir Soleil Anker-Baril**, sur Teams, ou à soleil.anker@ermco-eci.com.

Avant de venir, ces trois réflexes règlent la grande majorité des cas :

1. **Vérifiez sur quel affichage vous êtes** (en haut de la liste). C'est la cause numéro un de
   « il manque des unités ».
2. **Cherchez une icône d'entonnoir** dans les en-têtes, un filtre laissé par accident.
3. **L'affichage est-il regroupé ?** Si oui, voir la section 7, des groupes complets peuvent
   tomber en dehors de l'affichage sans que rien ne l'indique.

Si ce n'est aucun des trois : si une unité manque, si une colonne est vide alors qu'elle
devrait avoir une valeur, ou si quelque chose a l'air croche. **Ne travaillez pas autour et ne devinez pas.** Venez me voir. C'est un système neuf et trouver les défauts de jeunesse tout de
suite aide vraiment.
