"""Reglages gunicorn pour le backend de veille.

N'ECOUTE QUE SUR LA BOUCLE LOCALE. C'est le choix d'acces retenu : rien de ce
projet ne se presente sur l'internet public, ni le web ni la base. On y accede
par un tunnel SSH :

    ssh -N -L 8001:127.0.0.1:8001 utilisateur@serveur

puis http://127.0.0.1:8001 dans le navigateur. Le chiffrement est celui de
SSH ; il n'y a ni certificat a renouveler, ni nginx a tenir a jour, ni port
ouvert a surveiller.

Le jour ou l'interface devra etre publique, c'est ici que se branchera un
nginx -- et il faudra alors passer DERRIERE_TLS=1, sans quoi les
cookies de session ne seront pas marques Secure.
"""

import os

# Le serveur heberge deja une autre application : 8001 peut y etre pris.
# VEILLE_WEB_BIND permet de se decaler sans toucher a ce fichier. Le decalage
# doit alors etre reporte dans CSRF_TRUSTED_ORIGINS et dans le tunnel SSH,
# sans quoi toute connexion echouera en "CSRF verification failed".
bind = os.environ.get("VEILLE_WEB_BIND", "127.0.0.1:8001")

# Le backend ne fait que lire PostgreSQL : il attend la base bien plus qu'il
# ne calcule. Deux workers suffisent largement pour deux utilisateurs, et
# tiennent dans la RAM d'un petit serveur. La regle "2 x coeurs + 1" viserait
# un service charge, ce que celui-ci n'est pas.
workers = 2
threads = 2

# Une requete qui depasse la minute est une requete bloquee : la vue la plus
# lourde -- la carte, qui agrege 4000 offres -- rend en moins d'une seconde.
timeout = 60
graceful_timeout = 30

# Journalisation vers la sortie standard : systemd les recolte, `journalctl`
# les relit. Pas de fichier a faire tourner.
accesslog = "-"
errorlog = "-"
loglevel = "info"
