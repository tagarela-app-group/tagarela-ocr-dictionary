from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.vocabulary.models import Group, Term
from apps.vocabulary.tests.helpers import make_group, make_term

VOCABULARY = "/api/v1/vocabulary"
GROUPS = "/api/v1/groups"
MOVE = "/api/v1/terms/move"
DELETE = "/api/v1/terms/delete"
RESTORE = "/api/v1/terms/restore"


class VocabularyApiTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)


class VocabularyTests(VocabularyApiTestCase):
    def test_lists_groups_with_their_terms_and_the_ungrouped_ones(self):
        travel = make_group(self.user)
        jet_lag = make_term(self.user, "jet lag", travel, translation="cansaço da viagem", level=4)
        loose = make_term(self.user, "touch base")
        make_term(make_user("bia@example.com"), "carry-on")

        response = self.client.get(VOCABULARY)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "groups": [
                    {
                        "id": str(travel.id),
                        "name": "Viagem",
                        "icon": "travel",
                        "accent": "sky",
                        "terms": [
                            {
                                "id": str(jet_lag.id),
                                "text": "jet lag",
                                "translation": "cansaço da viagem",
                                "kind": "expression",
                                "level": 4,
                            }
                        ],
                    }
                ],
                "ungrouped": [
                    {
                        "id": str(loose.id),
                        "text": "touch base",
                        "translation": "",
                        "kind": "expression",
                        "level": 0,
                    }
                ],
            },
        )

    def test_newest_group_and_term_come_first(self):
        make_group(self.user, "Viagem")
        make_group(self.user, "Música")
        make_term(self.user, "mind")
        make_term(self.user, "gap")

        body = self.client.get(VOCABULARY).json()

        self.assertEqual([g["name"] for g in body["groups"]], ["Música", "Viagem"])
        self.assertEqual([t["text"] for t in body["ungrouped"]], ["gap", "mind"])

    def test_empty(self):
        response = self.client.get(VOCABULARY)

        self.assertEqual(response.json(), {"groups": [], "ungrouped": []})

    def test_requires_login(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get(VOCABULARY).status_code, 401)


class CreateGroupTests(VocabularyApiTestCase):
    def create(self, **data):
        payload = {"name": "Música", "icon": "music", "accent": "pink", **data}
        return self.client.post(GROUPS, payload, format="json")

    def test_creates_an_empty_group(self):
        response = self.create(name="  Séries   e filmes ")

        self.assertEqual(response.status_code, 201)
        group = Group.objects.get()
        self.assertEqual(group.user, self.user)
        self.assertEqual(
            response.json(),
            {
                "id": str(group.id),
                "name": "Séries e filmes",
                "icon": "music",
                "accent": "pink",
                "terms": [],
            },
        )

    def test_name_already_used_ignoring_case_returns_400(self):
        make_group(self.user, "Viagem")

        response = self.create(name="viagem")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"name": ["Você já tem um grupo com esse nome."]})

    def test_same_name_from_another_user_is_fine(self):
        make_group(make_user("bia@example.com"), "Música")

        self.assertEqual(self.create().status_code, 201)

    def test_invalid_fields_return_400(self):
        response = self.create(name=" ", icon="Not An Id", accent="black", extra=1)

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["name"], ["Dê um nome ao grupo."])
        self.assertIn("icon", body)
        self.assertIn("accent", body)
        self.assertEqual(body["extra"], ["Campo não permitido."])

    def test_name_too_long_returns_400(self):
        response = self.create(name="x" * 31)

        self.assertEqual(response.json(), {"name": ["O nome do grupo tem até 30 caracteres."]})


class MoveTermsTests(VocabularyApiTestCase):
    def move(self, terms, group):
        payload = {"terms": [str(t.id) for t in terms], "group": group and str(group.id)}
        return self.client.post(MOVE, payload, format="json")

    def test_moves_terms_and_returns_the_vocabulary(self):
        travel = make_group(self.user, "Viagem")
        music = make_group(self.user, "Música")
        carry_on = make_term(self.user, "carry-on", travel)
        jet_lag = make_term(self.user, "jet lag", travel)
        layover = make_term(self.user, "layover", travel)

        response = self.move([carry_on, jet_lag], music)

        self.assertEqual(response.status_code, 200)
        groups = {g["name"]: [t["text"] for t in g["terms"]] for g in response.json()["groups"]}
        self.assertEqual(groups, {"Música": ["jet lag", "carry-on"], "Viagem": ["layover"]})
        layover.refresh_from_db()
        self.assertEqual(layover.group, travel)

    def test_null_group_moves_back_to_ungrouped(self):
        term = make_term(self.user, "jet lag", make_group(self.user))

        response = self.move([term], None)

        self.assertEqual(response.json()["ungrouped"][0]["text"], "jet lag")
        term.refresh_from_db()
        self.assertIsNone(term.group)

    def test_group_from_another_user_returns_400(self):
        term = make_term(self.user, "jet lag")
        other = make_group(make_user("bia@example.com"))

        response = self.move([term], other)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"group": ["Esse grupo não existe mais."]})

    def test_term_from_another_user_returns_400_and_moves_nothing(self):
        mine = make_term(self.user, "jet lag")
        theirs = make_term(make_user("bia@example.com"), "layover")
        group = make_group(self.user)

        response = self.move([mine, theirs], group)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["Algum termo não existe mais."]})
        self.assertFalse(Term.objects.filter(group=group).exists())

    def test_without_terms_returns_400(self):
        response = self.client.post(MOVE, {"terms": [], "group": None}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["Escolha pelo menos um termo."]})


class GroupDetailTests(VocabularyApiTestCase):
    def url(self, group):
        return f"{GROUPS}/{group.id}"

    def test_updates_name_icon_and_accent(self):
        travel = make_group(self.user)
        term = make_term(self.user, "jet lag", travel)

        response = self.client.patch(
            self.url(travel),
            {"name": "  Viagens   longas ", "icon": "plane", "accent": "mint"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(travel.id),
                "name": "Viagens longas",
                "icon": "plane",
                "accent": "mint",
                "terms": [
                    {
                        "id": str(term.id),
                        "text": "jet lag",
                        "translation": "",
                        "kind": "expression",
                        "level": 0,
                    }
                ],
            },
        )

    def test_updates_only_what_was_sent(self):
        travel = make_group(self.user)

        self.client.patch(self.url(travel), {"accent": "pink"}, format="json")

        travel.refresh_from_db()
        self.assertEqual((travel.name, travel.icon, travel.accent), ("Viagem", "travel", "pink"))

    def test_same_name_with_other_case_is_fine(self):
        travel = make_group(self.user)

        response = self.client.patch(self.url(travel), {"name": "VIAGEM"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "VIAGEM")

    def test_name_of_another_group_returns_400(self):
        make_group(self.user, "Música")
        travel = make_group(self.user)

        response = self.client.patch(self.url(travel), {"name": "música"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"name": ["Você já tem um grupo com esse nome."]})

    def test_empty_body_returns_400(self):
        response = self.client.patch(self.url(make_group(self.user)), {}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_group_from_another_user_returns_404(self):
        other = make_group(make_user("bia@example.com"))

        patch = self.client.patch(self.url(other), {"name": "Minha"}, format="json")
        delete = self.client.delete(self.url(other))

        self.assertEqual((patch.status_code, delete.status_code), (404, 404))
        self.assertTrue(Group.objects.filter(pk=other.pk).exists())

    def test_delete_sends_its_terms_back_to_ungrouped(self):
        travel = make_group(self.user)
        make_term(self.user, "jet lag", travel)

        response = self.client.delete(self.url(travel))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["groups"], [])
        self.assertEqual([t["text"] for t in response.json()["ungrouped"]], ["jet lag"])


class DeleteTermsTests(VocabularyApiTestCase):
    def delete(self, *terms):
        return self.client.post(DELETE, {"terms": [str(t.id) for t in terms]}, format="json")

    def test_deleted_terms_leave_the_vocabulary(self):
        travel = make_group(self.user)
        jet_lag = make_term(self.user, "jet lag", travel)
        make_term(self.user, "layover", travel)
        loose = make_term(self.user, "touch base")

        response = self.delete(jet_lag, loose)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([t["text"] for t in response.json()["groups"][0]["terms"]], ["layover"])
        self.assertEqual(response.json()["ungrouped"], [])
        self.assertEqual(self.client.get(VOCABULARY).json(), response.json())

    def test_a_new_delete_drops_the_previous_one(self):
        old = make_term(self.user, "jet lag", deleted_at=timezone.now())
        layover = make_term(self.user, "layover")

        self.delete(layover)

        self.assertFalse(Term.objects.filter(pk=old.pk).exists())
        self.assertTrue(Term.objects.filter(pk=layover.pk).exists())

    def test_term_from_another_user_or_already_deleted_returns_400(self):
        mine = make_term(self.user, "jet lag")
        theirs = make_term(make_user("bia@example.com"), "layover")
        deleted = make_term(self.user, "carry-on", deleted_at=timezone.now())

        for terms in ([mine, theirs], [deleted]):
            response = self.delete(*terms)

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"terms": ["Algum termo não existe mais."]})
        mine.refresh_from_db()
        self.assertIsNone(mine.deleted_at)

    def test_deleted_term_cannot_be_moved(self):
        term = make_term(self.user, "jet lag", deleted_at=timezone.now())

        response = self.client.post(MOVE, {"terms": [str(term.id)], "group": None}, format="json")

        self.assertEqual(response.status_code, 400)


class RestoreTermsTests(VocabularyApiTestCase):
    def restore(self, *terms):
        return self.client.post(RESTORE, {"terms": [str(t.id) for t in terms]}, format="json")

    def test_restores_the_terms_to_their_group(self):
        travel = make_group(self.user)
        term = make_term(self.user, "jet lag", travel, level=3)
        self.client.post(DELETE, {"terms": [str(term.id)]}, format="json")

        response = self.restore(term)

        self.assertEqual(response.status_code, 200)
        restored = response.json()["groups"][0]["terms"][0]
        self.assertEqual((restored["text"], restored["level"]), ("jet lag", 3))

    def test_term_that_is_not_deleted_returns_400(self):
        response = self.restore(make_term(self.user, "jet lag"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["Não dá mais pra desfazer."]})
