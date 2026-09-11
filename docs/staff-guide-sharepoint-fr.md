# Travailler dans SharePoint : petit guide

> ### 📋 Brouillon à réviser, à publier le jour de la migration, puis effacer cet encadré
>
> Réécrit le 2026-09-09 pour la migration de jeudi. L'ancien avertissement disait que les deux
> consignes « n'écrivez plus dans le fichier Excel » étaient **à l'envers**, et il avait
> raison : pendant le fonctionnement parallèle, FRM10-12 était le seul classeur actif.
> **À la migration, elles deviennent justes**, donc l'avertissement est retiré et les deux
> consignes disent maintenant exactement ce qui est vrai, y compris ce que l'ancienne
> version passait sous silence : le fichier reste *consultable* et garde sa disposition
> habituelle.
>
> Nouveau depuis la dernière version : la section **« Ce qui a l'air différent »**. Le
> personnel ne change pas juste d'endroit où écrire, plusieurs champs passent d'une lettre
> tapée dans une case à une case à cocher ou à une liste déroulante, et personne ne l'avait
> écrit nulle part.
>
> **Ne pas faire circuler avant que la migration soit terminée.** D'ici là,
> `views-guide-sharepoint-fr.md` est ce qu'il faut dire au personnel.

## Ce qui arrive au fichier Excel

Il est encore là, et il a exactement la même allure : mêmes colonnes, même ordre, mêmes
valeurs. C'est maintenant une **copie en lecture seule** qui se reconstruit toute seule à
partir de SharePoint, alors consultez-le tant que vous voulez.

**La donnée voyage dans un seul sens, de SharePoint vers le fichier.** Rien de ce qui est
tapé dans le fichier ne se rend à SharePoint, et le prochain rafraîchissement l'efface. Si
vous voulez faire des changements, il faut les faire dans les listes SharePoint.

## Trouver votre travail

La liste s'ouvre dans l'affichage **`FRM10-12 Layout`**, qui est la disposition du
classeur : les mêmes colonnes, dans le même ordre que vous avez l'habitude. Vous devriez
vous y retrouver tout de suite, et il n'y a rien à choisir ni à régler avant.

**Ensuite, faites-vous en un à vous.** `FRM10-12 Layout` contient tout, ce qui veut dire
qu'il contient aussi beaucoup de choses que vous, personnellement, ne regardez jamais. Vous
pouvez vous bâtir un affichage avec seulement les colonnes dont vous avez besoin, trié et
regroupé selon votre façon de travailler, et il sera là chaque fois que vous ouvrez la
liste.

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

**`BO Tracking`** montre les mêmes unités regroupées par statut de BO, pour avoir au même
endroit tout ce qui attend une pièce.

Vous verrez aussi des affichages que des collègues se sont bâtis. En ouvrir un ne change
rien pour eux, alors regardez si ça vous sert. C'est la même liste de toute façon.

## Mettre une unité à jour

Cliquez dans la case. Écrivez. Passez à la suivante.

C'est tout. Il n'y a :

- **Aucun bouton d'enregistrement** : ça se sauvegarde à mesure
- **Aucun rafraîchissement à faire** : tout le monde voit votre changement immédiatement
- **Aucun « quelqu'un d'autre l'a ouvert »** : plusieurs personnes peuvent travailler en même
  temps

## Ce qui a l'air différent

La plupart des colonnes fonctionnent comme avant. Quelques-unes ont maintenant un vrai
contrôle au lieu d'une case où vous tapiez une lettre, la même information, sauf que ce
n'est plus une convention à retenir.

| ce que vous tapiez avant | maintenant |
|---|---|
| `R` dans **Tank**, **ISO Stack**, **ISO Coil**, **Lead Assembly** | une **case à cocher** |
| `x` dans **Temperature Rise**, **Impulse**, **Partial D**, **Oil Analysis**, **DB** | une **case à cocher** |
| `Y` dans **SFRA** | une **case à cocher** |
| `Reçu` ou `Plaspak` dans **Frame** | une **liste déroulante**, choisissez |
| du texte libre dans **Order Type**, **Order Step**, **Order Status**, **Indexing**, **WET-WETP**, **Client Date Status**, **Core Type**, **Family**, **Model Type**, **Oil Type**, **Modification Status**, **New model to be created** | une **liste déroulante**, choisissez |
| un code comme `TE-Se-4` dans **Status** | deux champs : **Step Status** (choisir l'étape) et **Status Date** (choisir la date) |

Quelques choses à savoir :

- **Décochée veut dire « non ».** Il n'y a pas de troisième option pour « pas encore
  décidé ». Si vous avez besoin de cette option-là, venez me voir.
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

## Quelque chose cloche ?

**Venez voir Soleil Anker-Baril**, sur Teams, ou à soleil.anker@ermco-eci.com.

Si une unité manque, si une colonne est vide, ou si quelque chose a l'air croche. Ne travaillez pas autour et ne devinez pas. Venez me voir. C'est un nouveau système, et trouver
les défauts de jeunesse tout de suite aide vraiment.
