# Travailler dans SharePoint : petit guide

> ### 📋 Brouillon à réviser, à publier le jour de la bascule, puis effacer cet encadré
>
> Réécrit le 2026-09-09 pour la bascule de jeudi. L'ancien avertissement disait que les deux
> consignes « n'écrivez plus dans le fichier Excel » étaient **à l'envers**, et il avait
> raison : pendant le fonctionnement parallèle, FRM10-12 était le seul classeur actif.
> **À la bascule, elles deviennent justes**, donc l'avertissement est retiré et les deux
> consignes disent maintenant exactement ce qui est vrai, y compris ce que l'ancienne
> version passait sous silence : le fichier reste *consultable* et garde sa disposition
> habituelle.
>
> Nouveau depuis la dernière version : la section **« Ce qui a l'air différent »**. Le
> personnel ne change pas juste d'endroit où écrire, plusieurs champs passent d'une lettre
> tapée dans une case à une case à cocher ou à une liste déroulante, et personne ne l'avait
> écrit nulle part.
>
> **Ne pas faire circuler avant que la bascule soit terminée.** D'ici là,
> `views-guide-sharepoint-fr.md` est ce qu'il faut dire au personnel.

## Ce qui change

Le suivi de production sort du fichier Excel FRM10-12 et s'en vient dans SharePoint. Vous
mettez maintenant vos unités à jour directement dans une liste sur ce site, au lieu d'ouvrir
le classeur. Plus besoin d'attendre que quelqu'un d'autre ferme le fichier, et plus de
changements perdus.

Le fichier Excel existe encore, et il a exactement la même allure, mêmes colonnes, même
ordre, mêmes valeurs. C'est maintenant une **copie en lecture seule** qui se reconstruit
toute seule à partir de SharePoint. Consultez-le tant que vous voulez. Vos changements, eux,
se font dans SharePoint.

## Trouver votre travail

Ouvrez l'affichage (*view*) **Production Floor**.

Il montre seulement ce qui compte quand vous suivez une commande : le numéro d'unité, le
numéro de commande, où l'unité est rendue, qui la bobine, et quand elle est due. Tout le
reste est masqué.

Les unités sont **regroupées par Location** : l'étape de production : `Bobinage`, `Stacking`,
`Assemblage`, `Four`, `Tanking`, `Test`, `Finition`, `Livraison`, et les autres que vous
connaissez déjà. Toutes les unités rendues à la même étape apparaissent ensemble sous un même
titre, et vous pouvez replier un groupe qui ne vous concerne pas. Ça se lit comme un tableau
de production, pas comme un chiffrier.

Chaque Location a **sa propre couleur**, ce qui permet de voir d'un coup d'œil où l'ouvrage
s'accumule.

Dans chaque groupe, l'unité la plus pressante est en haut, trié par date due.

Seul l'ouvrage actif s'affiche. Les unités marquées livrées ou annulées disparaissent de
l'affichage toutes seules.

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

## Si vous préférez l'ancienne disposition

Ouvrez plutôt l'affichage **Planning**. C'est la disposition **repliée** du classeur, les
mêmes colonnes, dans le même ordre, que celles que vous voyez dans FRM10-12 quand les
groupes de colonnes sont fermés. Si vous avez besoin d'une colonne de détail que vous
ouvririez normalement, elles sont toutes encore là dans l'affichage **All Items**.

## S.V.P., ne pas faire

**N'écrivez plus dans le fichier Excel.** C'est un miroir maintenant : il se reconstruit à
partir de SharePoint, donc tout ce qui est tapé dedans est effacé au prochain
rafraîchissement et ne se rend jamais dans SharePoint. Vous allez probablement voir que vous
ne pouvez plus écrire dedans du tout, il est mis en lecture seule, mais si jamais vous
êtes capable, c'est une erreur à signaler, pas une invitation.

**Ne travaillez pas autour d'un problème.** Voir plus bas.

## Quelque chose cloche ?

**Venez voir Soleil Anker-Baril**, sur Teams, ou à soleil.anker@ermco-eci.com.

Si une unité manque, si une colonne est vide, ou si quelque chose a l'air croche. Ne travaillez pas autour et ne devinez pas. Venez me voir. C'est un nouveau système, et trouver
les défauts de jeunesse tout de suite aide vraiment.
