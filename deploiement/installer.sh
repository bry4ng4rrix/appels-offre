#!/usr/bin/env bash
#
# Installation de la veille sur le serveur.
#
#   sudo bash installer.sh
#
# A LIRE AVANT DE LANCER. Ce script tourne en root sur une machine qui porte
# deja une autre application (sophie-agent). Il a ete ecrit pour ne rien
# toucher qui ne lui appartienne :
#
#   - il ne modifie AUCUN fichier existant, nginx compris. La mise en place
#     du proxy /api/ reste manuelle, section 7 bis du guide, parce qu'elle
#     edite le fichier d'une autre application ;
#   - il n'installe aucun paquet : tout est deja present, il verifie ;
#   - il ne touche ni au pare-feu, ni aux ports 80/443, ni aux services
#     existants ;
#   - il s'arrete a la premiere erreur, sans laisser d'etat a moitie pose.
#
# Ce qu'il cree, et rien d'autre :
#   /opt/veille/            repertoire, utilisateur systeme "veille"
#   /opt/veille/app/        le depot clone
#   /opt/veille/venv/       l'environnement Python
#   /opt/veille/.env        les secrets, engendres ici
#   conteneur veille_db     PostgreSQL, sur 127.0.0.1:5433
#   3 unites systemd        veille-web, veille-collecte, veille-collecte.timer
#
# Il est REJOUABLE : le relancer apres correction d'une erreur reprend ou il
# s'etait arrete, sans rien casser de ce qui etait deja fait.

set -euo pipefail

DEPOT="git@github.com:labeltechnology/veille-appels.git"
RACINE="/opt/veille"
APP="$RACINE/app"
VENV="$RACINE/venv"
ENVF="$RACINE/.env"
UTILISATEUR="veille"

vert()  { printf '\033[32m%s\033[0m\n' "$*"; }
jaune() { printf '\033[33m%s\033[0m\n' "$*"; }
rouge() { printf '\033[31m%s\033[0m\n' "$*"; }
titre() { printf '\n\033[1m=== %s ===\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { rouge "A lancer avec sudo."; exit 1; }


titre "1/8  Verifications"

# Chacune de ces conditions, si elle manquait, ferait echouer une etape plus
# loin avec un message bien moins clair.
manque=0
verifier() {
    printf '  %-34s ' "$1"
    if eval "$2" >/dev/null 2>&1; then vert "ok"; else rouge "MANQUE"; manque=1; fi
}
verifier "python3 >= 3.12"      "python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'"
verifier "python3-venv"         "python3 -m venv --help"
verifier "git"                  "command -v git"
verifier "docker"               "docker info"
verifier "docker compose v2"    "docker compose version"
[ "$manque" -eq 0 ] || { rouge "Corriger ce qui manque avant de relancer."; exit 1; }

# Les ports sont verifies APRES, car le conteneur de la veille peut deja les
# occuper lors d'un second passage : c'est alors normal, pas un conflit.
for port in 5433 8001; do
    printf '  %-34s ' "port $port"
    if ss -lnt "sport = :$port" 2>/dev/null | grep -q ":$port"; then
        if [ "$port" = 5433 ] && docker ps --format '{{.Names}}' | grep -qx veille_db; then
            jaune "pris par veille_db (deja installe)"
        elif [ "$port" = 8001 ] && systemctl is-active --quiet veille-web 2>/dev/null; then
            jaune "pris par veille-web (deja installe)"
        else
            rouge "PRIS par autre chose"
            rouge "  -> definir VEILLE_DB_PORT / VEILLE_WEB_BIND, section 2 bis du guide"
            exit 1
        fi
    else
        vert "libre"
    fi
done


titre "2/8  Compte de service"

if id "$UTILISATEUR" >/dev/null 2>&1; then
    jaune "  utilisateur $UTILISATEUR deja present"
else
    useradd --system --create-home --home-dir "$RACINE" --shell /usr/sbin/nologin "$UTILISATEUR"
    vert "  utilisateur $UTILISATEUR cree"
fi

# Sans ce groupe, le compte ne peut pas parler au demon Docker et l'etape 5
# echouerait sur "permission denied".
if id -nG "$UTILISATEUR" | tr ' ' '\n' | grep -qx docker; then
    jaune "  deja dans le groupe docker"
else
    usermod -aG docker "$UTILISATEUR"
    vert "  ajoute au groupe docker"
fi


titre "3/8  Cle de deploiement"

CLE="$RACINE/.ssh/id_ed25519"
install -d -m 700 -o "$UTILISATEUR" -g "$UTILISATEUR" "$RACINE/.ssh"
if [ -f "$CLE" ]; then
    jaune "  cle deja presente"
else
    sudo -u "$UTILISATEUR" ssh-keygen -t ed25519 -f "$CLE" -N "" -C "veille@$(hostname)" >/dev/null
    vert "  cle creee"
fi

# github.com dans known_hosts : sans lui, le clone s'arrete sur une question
# a laquelle personne ne repondra.
sudo -u "$UTILISATEUR" ssh-keyscan -t ed25519 github.com 2>/dev/null \
    >> "$RACINE/.ssh/known_hosts"
sudo -u "$UTILISATEUR" sort -u -o "$RACINE/.ssh/known_hosts" "$RACINE/.ssh/known_hosts"
chmod 600 "$RACINE/.ssh/known_hosts"


titre "4/8  Depot"

if [ -d "$APP/.git" ]; then
    jaune "  depot deja clone, mise a jour"
    sudo -u "$UTILISATEUR" git -C "$APP" pull --ff-only
else
    if ! sudo -u "$UTILISATEUR" git clone "$DEPOT" "$APP" 2>/dev/null; then
        rouge ""
        rouge "  Le clone a echoue : la cle de deploiement n'est pas autorisee."
        rouge ""
        echo  "  1. Ouvrir  https://github.com/labeltechnology/veille-appels/settings/keys"
        echo  "  2. 'Add deploy key', SANS cocher 'Allow write access'"
        echo  "  3. Coller la cle ci-dessous"
        echo  "  4. Relancer ce script -- il reprendra ici"
        rouge ""
        cat "$CLE.pub"
        rouge ""
        exit 1
    fi
    vert "  depot clone"
fi


titre "5/8  Environnement Python"

if [ -d "$VENV" ]; then
    jaune "  venv deja present"
else
    sudo -u "$UTILISATEUR" python3 -m venv "$VENV"
    vert "  venv cree"
fi
sudo -u "$UTILISATEUR" "$VENV/bin/pip" install --quiet --upgrade pip
sudo -u "$UTILISATEUR" "$VENV/bin/pip" install --quiet \
    -r "$APP/requirements.txt"
vert "  dependances installees"


titre "6/8  Secrets"

if [ -f "$ENVF" ]; then
    jaune "  .env deja present, laisse intact"
    jaune "  (SECRET_KEY ne doit JAMAIS changer : la modifier"
    jaune "   deconnecterait tout le monde sans message clair)"
else
    MDP=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    CLE_DJ=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    cat > "$ENVF" <<FIN
# Engendre par installer.sh le $(date -Iseconds).
# SECRET_KEY signe les sessions : ne jamais la changer.
POSTGRES_DB=veille
POSTGRES_USER=veille
POSTGRES_PASSWORD=$MDP
DATABASE_URL=postgresql://veille:$MDP@127.0.0.1:5433/veille
DEBUG=false
SECRET_KEY=$CLE_DJ
ALLOWED_HOSTS=andryvoip.duckdns.org,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://andryvoip.duckdns.org,http://127.0.0.1:8001,http://localhost:8001
# Passe a 1 une fois le proxy nginx en place (section 7 bis du guide).
DERRIERE_TLS=0
FIN
    chown "$UTILISATEUR:$UTILISATEUR" "$ENVF"
    chmod 600 "$ENVF"
    vert "  .env cree, deux secrets engendres"
fi


titre "7/8  Base de donnees"

cd "$APP"
sudo -u "$UTILISATEUR" docker compose -f deploiement/docker-compose.yml \
    --env-file "$ENVF" up -d
printf '  attente de PostgreSQL '
for _ in $(seq 60); do
    if docker exec veille_db pg_isready -U veille -d veille >/dev/null 2>&1; then break; fi
    printf '.'; sleep 1
done
docker exec veille_db pg_isready -U veille -d veille >/dev/null 2>&1 \
    || { rouge " la base ne repond pas"; exit 1; }
vert " prete"

# set -a exporte tout ce que .env definit, ce dont manage.py a besoin.
sudo -u "$UTILISATEUR" bash -c "set -a; . '$ENVF'; set +a
    '$VENV/bin/python' '$APP/manage.py' migrate --noinput
    '$VENV/bin/python' '$APP/manage.py' collectstatic --noinput" >/dev/null
vert "  schema Django et fichiers statiques en place"


titre "8/8  Services"

for f in veille-web.service veille-collecte.service veille-collecte.timer; do
    # Les unites portent deja les bons chemins : depot dans /opt/veille/app,
    # venv et .env a la racine /opt/veille. Elles sont copiees telles quelles.
    # Une premiere version les reecrivait au vol par sed, et la reecriture
    # etait incomplete -- --config et --chdir pointaient a cote.
    install -m 644 "$APP/deploiement/$f" "/etc/systemd/system/$f"
done
systemctl daemon-reload
systemctl enable --now veille-web.service
systemctl enable --now veille-collecte.timer
vert "  services poses et demarres"

sleep 2
titre "Resultat"
systemctl is-active veille-web.service >/dev/null \
    && vert "  veille-web        active" \
    || { rouge "  veille-web       EN ECHEC"; journalctl -u veille-web -n 20 --no-pager; }
printf '  interface locale  ' ; curl -s -o /dev/null -w '%{http_code} (200 attendu)\n' http://127.0.0.1:8001/
printf '  api sans jeton    ' ; curl -s -o /dev/null -w '%{http_code} (401 attendu)\n' http://127.0.0.1:8001/api/offres/
systemctl list-timers veille-collecte.timer --no-pager | tail -2

cat <<'FIN'

Reste a faire A LA MAIN, volontairement :

  1. Les 4 000 offres existantes  -> section 10 du guide.

  2. Le proxy /api/ pour le site public -> section 7 bis. NON automatise :
     il edite /etc/nginx/conf.d/sophie-agent.conf, qui appartient a une autre
     application. A faire en connaissance de cause, apres sauvegarde.

Depuis le poste, tunnel ouvert :  http://127.0.0.1:8001
FIN
