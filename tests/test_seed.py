import uuid
from datetime import datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from mathutrice import models
from mathutrice.referentiel import REFERENTIEL
from mathutrice.fonctions_python.seed import seed_if_empty


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def rows(session, model):
    return session.exec(select(model)).all()


def counts(session):
    return tuple(
        len(rows(session, model))
        for model in (models.Notion, models.Competence, models.User)
    )


def test_seeds_every_notion_of_the_referentiel(session):
    seed_if_empty(session, with_users=False)

    notions = {n.referentiel_key: n for n in rows(session, models.Notion)}
    assert set(notions) == set(REFERENTIEL)
    for key, notion in notions.items():
        assert isinstance(notion.notion_id, uuid.UUID)
        assert notion.title == REFERENTIEL[key]["notion_nom"]
        assert notion.description


def test_seeds_every_competence_under_its_notion(session):
    seed_if_empty(session, with_users=False)

    competences = {c.referentiel_code: c for c in rows(session, models.Competence)}
    expected = {
        comp["code"]: (key, comp)
        for key, data in REFERENTIEL.items()
        for comp in data["competences"]
    }
    assert set(competences) == set(expected)
    for code, competence in competences.items():
        notion_key, comp = expected[code]
        assert competence.notion.referentiel_key == notion_key
        assert competence.title == comp["nom"]
        assert competence.level == comp["niveau"]


def test_seeds_one_user_per_role_with_the_right_domain(session):
    seed_if_empty(session, with_users=True)

    users = {u.role: u for u in rows(session, models.User)}
    assert sorted(users) == ["Admin", "Student", "Teacher"]
    assert users["Student"].email.endswith("@epfedu.fr")
    assert users["Teacher"].email.endswith("@epf.fr")
    assert users["Admin"].email.endswith("@epf.fr")


def test_seeds_no_user_when_asked_not_to(session):
    seed_if_empty(session, with_users=False)

    assert rows(session, models.User) == []


def test_second_run_changes_nothing(session):
    seed_if_empty(session, with_users=True)
    before = counts(session)

    seed_if_empty(session, with_users=True)

    assert counts(session) == before


def test_existing_notions_are_left_alone(session):
    session.add(
        models.Notion(
            notion_id=uuid.uuid4(),
            referentiel_key="trigonometrie",
            title="Trigo maison",
            description="Déjà là",
        )
    )
    session.commit()

    seed_if_empty(session, with_users=False)

    assert [n.title for n in rows(session, models.Notion)] == ["Trigo maison"]
    assert rows(session, models.Competence) == []


def test_existing_users_are_left_alone_but_notions_still_arrive(session):
    session.add(
        models.User(
            sso_id=uuid.uuid4(),
            created_at=datetime(2026, 1, 1),
            role="Student",
            email="deja.la@epfedu.fr",
            name="Déjà Là",
        )
    )
    session.commit()

    seed_if_empty(session, with_users=True)

    assert [u.email for u in rows(session, models.User)] == ["deja.la@epfedu.fr"]
    assert len(rows(session, models.Notion)) == len(REFERENTIEL)
