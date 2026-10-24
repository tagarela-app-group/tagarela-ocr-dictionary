from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.vocabulary.models import Group, Term
from apps.vocabulary.tests.helpers import make_group, make_term

VOCABULARY = "/api/v1/vocabulary"
GROUPS = "/api/v1/groups"
MOVE = "/api/v1/terms/move"


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
