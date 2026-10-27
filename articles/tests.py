from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from articles.models import (
    Article,
    ArticleVersion,
    Annotation,
    annotations_se_chevauchent,)


class AnnotationsSeChevauchentTests(TestCase):
    """Teste la fonction pure annotations_se_chevauchent."""

    def test_suppression_suppression_chevauche(self):
        a = Annotation(type="suppression", debut=10, fin=20)
        b = Annotation(type="suppression", debut=15, fin=25)
        self.assertTrue(annotations_se_chevauchent(a, b))

    def test_suppression_suppression_disjointes(self):
        a = Annotation(type="suppression", debut=10, fin=20)
        c = Annotation(type="suppression", debut=30, fin=40)
        self.assertFalse(annotations_se_chevauchent(a, c))

    def test_suppression_insertion_chevauche(self):
        a = Annotation(type="suppression", debut=10, fin=20)
        d = Annotation(type="insertion", debut=15, fin=15)
        self.assertTrue(annotations_se_chevauchent(a, d))

    def test_insertion_insertion_meme_position(self):
        d1 = Annotation(type="insertion", debut=15, fin=15)
        d2 = Annotation(type="insertion", debut=15, fin=15)
        self.assertTrue(annotations_se_chevauchent(d1, d2))

    def test_commentaire_ignore(self):
        a = Annotation(type="suppression", debut=10, fin=20)
        e = Annotation(type="commentaire", debut=15, fin=25)
        self.assertFalse(annotations_se_chevauchent(a, e))
        self.assertFalse(annotations_se_chevauchent(e, a))

    def test_adjacence_ne_chevauche_pas(self):
        # [10, 20[ et [20, 30[ ne se chevauchent pas
        a = Annotation(type="suppression", debut=10, fin=20)
        c = Annotation(type="suppression", debut=20, fin=30)
        self.assertFalse(annotations_se_chevauchent(a, c))


class AnnotationValidationTests(TestCase):
    """Teste la validation du modèle Annotation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            password="test",
            role="redacteur",
        )
        cls.article = Article.objects.create(
            titre="Article test",
            redacteur=cls.user,
            contenu="Lorem ipsum dolor sit amet.",
        )
        cls.version = ArticleVersion.objects.create(
            article=cls.article,
            numero=1,
            contenu=cls.article.contenu,
        )

    def test_suppression_valide(self):
        ann = Annotation.objects.create(
            article=self.article,
            version=self.version,
            redacteur=self.user,
            type="suppression",
            debut=0,
            fin=5,
        )
        self.assertEqual(ann.statut, "proposee")

    def test_suppression_sans_texte_propose(self):
        # Une suppression ne doit pas avoir de texte proposé
        with self.assertRaises(ValidationError):
            Annotation.objects.create(
                article=self.article,
                version=self.version,
                redacteur=self.user,
                type="suppression",
                debut=0,
                fin=5,
                texte_propose="un texte",
            )

    def test_insertion_valide(self):
        ann = Annotation.objects.create(
            article=self.article,
            version=self.version,
            redacteur=self.user,
            type="insertion",
            debut=5,
            fin=5,
            texte_propose="nouveau",
        )
        self.assertEqual(ann.debut, ann.fin)

    def test_insertion_debut_diff_fin_invalide(self):
        with self.assertRaises(ValidationError):
            Annotation.objects.create(
                article=self.article,
                version=self.version,
                redacteur=self.user,
                type="insertion",
                debut=5,
                fin=10,
                texte_propose="nouveau",
            )

    def test_insertion_sans_texte_invalide(self):
        with self.assertRaises(ValidationError):
            Annotation.objects.create(
                article=self.article,
                version=self.version,
                redacteur=self.user,
                type="insertion",
                debut=5,
                fin=5,
            )

    def test_remplacement_valide(self):
        ann = Annotation.objects.create(
            article=self.article,
            version=self.version,
            redacteur=self.user,
            type="remplacement",
            debut=0,
            fin=5,
            texte_propose="nouveau",
        )
        self.assertEqual(ann.type, "remplacement")

    def test_commentaire_valide(self):
        ann = Annotation.objects.create(
            article=self.article,
            version=self.version,
            redacteur=self.user,
            type="commentaire",
            debut=0,
            fin=10,
            commentaire="à vérifier",
        )
        self.assertEqual(ann.type, "commentaire")

    def test_debut_superieur_a_fin_invalide(self):
        with self.assertRaises(ValidationError):
            Annotation.objects.create(
                article=self.article,
                version=self.version,
                redacteur=self.user,
                type="suppression",
                debut=20,
                fin=10,
            )