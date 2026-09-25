"""
seed.py — Remplit une base vide avec des données représentatives

Appelé à chaque démarrage de l'application (create_db_and_tables dans app.py) :
  - notions et compétences, reprises du REFERENTIEL
  - un utilisateur par rôle, seulement si demandé (AUTH_MODE=dev)

Chaque partie n'est insérée que si sa table est vide : une base
qui contient déjà des données n'est jamais modifiée.
"""

import uuid
from datetime import datetime, UTC

from sqlmodel import Session, select

from mathutrice import models
from mathutrice.fonctions_python.main import REFERENTIEL


# Le REFERENTIEL ne porte pas de description : elles vivent ici,
# indexées par la même clé que Notion.referentiel_key.
DESCRIPTIONS = {
    "trigonometrie": "Étude des fonctions trigonométriques, des angles et du cercle trigonométrique.",
    "fractions_puissances_radicaux": "Manipulation des fractions, puissances et radicaux.",
    "logarithme_exponentielle": "Étude des fonctions logarithme et exponentielle.",
    "manipulation_expressions_litterales": "Isolement et manipulation de variables dans des expressions algébriques.",
    "equations_inequations": "Résolution d'équations et d'inéquations du premier et second degré.",
    "polynomes_factorisation": "Étude des polynômes, factorisation et identités remarquables.",
    "analyse_dimensionnelle": "Dimensions, unités et homogénéité des formules physiques.",
}

# (rôle, email, nom) — Student en @epfedu.fr, Teacher et Admin en @epf.fr.
USERS = [
    ("Student", "etudiant.demo@epfedu.fr", "Étudiant Démo"),
    ("Teacher", "enseignant.demo@epf.fr", "Enseignant Démo"),
    ("Admin", "admin.demo@epf.fr", "Admin Démo"),
]


def _is_empty(session: Session, model) -> bool:
    return session.exec(select(model).limit(1)).first() is None


def _seed_referentiel(session: Session) -> None:
    for notion_key, notion_data in REFERENTIEL.items():
        notion = models.Notion(
            notion_id=uuid.uuid4(),
            referentiel_key=notion_key,
            title=notion_data["notion_nom"],
            description=DESCRIPTIONS.get(notion_key, notion_data["notion_nom"]),
        )
        session.add(notion)

        for comp in notion_data["competences"]:
            session.add(
                models.Competence(
                    competence_id=uuid.uuid4(),
                    referentiel_code=comp["code"],
                    title=comp["nom"],
                    level=comp["niveau"],
                    notion_id=notion.notion_id,
                )
            )


def _seed_users(session: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    for role, email, name in USERS:
        session.add(
            models.User(
                sso_id=uuid.uuid4(),
                created_at=now,
                role=role,
                email=email,
                name=name,
            )
        )


def seed_if_empty(session: Session, *, with_users: bool) -> None:
    """Insère notions, compétences et (si with_users) un utilisateur par rôle,
    chaque partie seulement si sa table est vide."""
    if _is_empty(session, models.Notion):
        _seed_referentiel(session)
        print(f"[SEED] {len(REFERENTIEL)} notions et leurs compétences insérées.")

    if with_users and _is_empty(session, models.User):
        _seed_users(session)
        print(f"[SEED] Utilisateurs insérés : {', '.join(e for _, e, _ in USERS)}")

    session.commit()
