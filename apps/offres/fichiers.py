"""Controle des fichiers deposes (CV, photo de profil).

On ne croit ni l'extension ni le type annonce par le navigateur : les premiers
octets doivent correspondre au format. SVG refuse (il peut porter du script).
"""

import os
import zipfile

from django.core.exceptions import ValidationError

TAILLE_CV = 5 * 1024 * 1024
TAILLE_PHOTO = 2 * 1024 * 1024

#: Extension -> type MIME servi pour les photos.
TYPES_PHOTO = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp"}


def _entete(fichier, n: int) -> bytes:
    fichier.seek(0)
    debut = fichier.read(n)
    fichier.seek(0)
    return debut


def verifier_cv(fichier):
    ext = os.path.splitext(fichier.name)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise ValidationError("Format refusé : PDF ou DOCX uniquement.")
    if fichier.size > TAILLE_CV:
        raise ValidationError("Fichier trop lourd : 5 Mo au maximum.")
    if ext == ".pdf":
        if not _entete(fichier, 5) == b"%PDF-":
            raise ValidationError("Ce fichier n'est pas un PDF valide.")
        return
    # DOCX = archive ZIP contenant word/document.xml.
    try:
        fichier.seek(0)
        with zipfile.ZipFile(fichier) as archive:
            valide = "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        valide = False
    finally:
        fichier.seek(0)
    if not valide:
        raise ValidationError("Ce fichier n'est pas un document Word (.docx) valide.")


def verifier_photo(fichier):
    ext = os.path.splitext(fichier.name)[1].lower()
    if ext not in TYPES_PHOTO:
        raise ValidationError("Format refusé : PNG, JPEG ou WebP.")
    if fichier.size > TAILLE_PHOTO:
        raise ValidationError("Image trop lourde : 2 Mo au maximum.")
    debut = _entete(fichier, 12)
    if not (debut.startswith(b"\x89PNG\r\n\x1a\n") or debut.startswith(b"\xff\xd8\xff")
            or (debut[:4] == b"RIFF" and debut[8:12] == b"WEBP")):
        raise ValidationError("Ce fichier n'est pas une image valide.")
