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
            auteur=cls.user,
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
            auteur=self.user,
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
                auteur=self.user,
                type="suppression",
                debut=0,
                fin=5,
                texte_propose="un texte",
            )

    def test_insertion_valide(self):
        ann = Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
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
                auteur=self.user,
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
                auteur=self.user,
                type="insertion",
                debut=5,
                fin=5,
            )

    def test_remplacement_valide(self):
        ann = Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
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
            auteur=self.user,
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
                auteur=self.user,
                type="suppression",
                debut=20,
                fin=10,
            )


class ArticleMethodesTests(TestCase):
    """Teste version_courante, texte_final, nombre_signes."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="redacteur",
            password="test",
            role="redacteur",
        )
        cls.article = Article.objects.create(
            titre="Article test",
            auteur=cls.user,
            contenu="abcdef",
        )
        cls.version = ArticleVersion.objects.create(
            article=cls.article,
            numero=1,
            contenu=cls.article.contenu,
        )

    def test_version_courante(self):
        v = self.article.version_courante()
        self.assertEqual(v, self.version)

    def test_version_courante_renvoie_la_plus_recente(self):
        ArticleVersion.objects.create(
            article=self.article,
            numero=2,
            contenu="deuxième",
        )
        v = self.article.version_courante()
        self.assertEqual(v.numero, 2)

    def test_version_courante_sans_version(self):
        article_vide = Article.objects.create(
            titre="Sans version",
            auteur=self.user,
        )
        self.assertIsNone(article_vide.version_courante())

    def test_texte_final_sans_annotation(self):
        self.assertEqual(self.article.texte_final(), "abcdef")

    def test_texte_final_avec_suppression_acceptee(self):
        # Supprime "bcd" (positions 1 à 4)
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="suppression",
            debut=1,
            fin=4,
            statut="acceptee",
        )
        self.assertEqual(self.article.texte_final(), "aef")

    def test_texte_final_avec_insertion_acceptee(self):
        # Insère "XYZ" à la position 3 (entre "c" et "d")
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="insertion",
            debut=3,
            fin=3,
            texte_propose="XYZ",
            statut="acceptee",
        )
        self.assertEqual(self.article.texte_final(), "abcXYZdef")

    def test_texte_final_avec_remplacement_accepte(self):
        # Remplace "bcd" (positions 1 à 4) par "X"
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="remplacement",
            debut=1,
            fin=4,
            texte_propose="X",
            statut="acceptee",
        )
        self.assertEqual(self.article.texte_final(), "aXef")

    def test_texte_final_ignore_annotations_non_acceptees(self):
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="suppression",
            debut=1,
            fin=4,
            statut="proposee",
        )
        self.assertEqual(self.article.texte_final(), "abcdef")

    def test_texte_final_plusieurs_annotations(self):
        # Supprime "bc" (1-3), puis insère "Z" à la position 4 (avant "e")
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="suppression",
            debut=1,
            fin=3,
            statut="acceptee",
        )
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="insertion",
            debut=4,
            fin=4,
            texte_propose="Z",
            statut="acceptee",
        )
        # Application de la fin vers le début :
        # 1) insertion Z à 4 dans "abcdef" → "abcdZef"
        # 2) suppression bc [1,3[ dans "abcdZef" → "adZef"
        self.assertEqual(self.article.texte_final(), "adZef")

    def test_nombre_signes(self):
        self.assertEqual(self.article.nombre_signes(), 6)

    def test_nombre_signes_apres_suppression(self):
        Annotation.objects.create(
            article=self.article,
            version=self.version,
            auteur=self.user,
            type="suppression",
            debut=1,
            fin=4,
            statut="acceptee",
        )
        # "aef" → 3 caractères
        self.assertEqual(self.article.nombre_signes(), 3)