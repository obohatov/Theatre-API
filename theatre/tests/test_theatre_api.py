import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from theatre.models import Play, Performance, TheatreHall, Genre, Actor
from theatre.serializers import (
    PlayListSerializer,
    PlayDetailSerializer,
)

PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Play.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = TheatreHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "play": None,
        "theatre_hall": theatre_hall,
    }
    defaults.update(params)

    return Performance.objects.create(**defaults)


def image_upload_url(play_id):
    return reverse("theatre:play-upload-image", args=[play_id])


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


class TheatreImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.play = sample_play()
        self.performance = sample_performance(play=self.play)

    def tearDown(self):
        self.play.image.delete()

    def test_upload_image_to_play(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.play.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.play.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.play.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_url_is_shown_on_play_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.play.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_play_list(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PLAY_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_performance_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PERFORMANCE_URL)

        self.assertIn("play_image", res.data[0].keys())


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_requires(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "realuser@test.com",
            "securepassword",
        )
        self.client.force_authenticate(self.user)

    def test_list_plays(self):
        sample_play(title="Macbeth", duration=169)
        play_with_genre = sample_play(title="Othello", duration=148)
        play_with_actors = sample_play(title="Hamlet", duration=152)

        genre = Genre.objects.create(name="Tragedy")
        actor = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")

        play_with_genre.genres.add(genre)
        play_with_actors.actors.add(actor)

        res = self.client.get(PLAY_URL)

        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_plays_by_genre(self):
        play1 = sample_play(title="Othello")
        play2 = sample_play(title="Hamlet")

        genre1 = Genre.objects.create(name="Tragedy")
        genre2 = Genre.objects.create(name="Thriller")

        play1.genres.add(genre1)
        play2.genres.add(genre2)

        play3 = sample_play(title="TMacbeth")

        res = self.client.get(PLAY_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_plays_by_actor(self):
        play1 = sample_play(title="Othello")
        play2 = sample_play(title="Hamlet")

        actor1 = Actor.objects.create(first_name="Matthew", last_name="McConaughey")
        actor2 = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")

        play1.actors.add(actor1)
        play2.actors.add(actor2)

        play3 = sample_play(title="Macbeth")

        res = self.client.get(PLAY_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_plays_by_title(self):
        play1 = sample_play(title="Othello")
        play2 = sample_play(title="Hamlet")

        res = self.client.get(PLAY_URL, {"title": f"{play1.title}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_play_detail(self):
        play = sample_play(title="Othello")
        play.genres.add(Genre.objects.create(name="Tragedy"))
        play.actors.add(
            Actor.objects.create(first_name="Matthew", last_name="McConaughey")
        )

        url = detail_url(play.id)
        res = self.client.get(url)

        serializer = PlayDetailSerializer(play)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_play_forbidden(self):
        payload = {
            "title": "Macbeth",
            "description": "A brave Scottish general named Macbeth receives a prophecy",
            "duration": 169,
        }

        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com", "securepassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_play_with_genres_and_actors(self):
        genre1 = Genre.objects.create(name="Tragedy")
        genre2 = Genre.objects.create(name="Comedy")

        actor1 = Actor.objects.create(first_name="Matthew", last_name="McConaughey")
        actor2 = Actor.objects.create(first_name="Anne", last_name="Hathaway")

        payload = {
            "title": "Macbeth",
            "description": "A brave Scottish general named Macbeth receives a prophecy",
            "duration": 169,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(PLAY_URL, payload)

        play = Play.objects.get(id=res.data["id"])
        genres = play.genres.all()
        actors = play.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_delete_and_put_movie_not_allowed(self):
        play = sample_play(title="Macbeth")
        url = detail_url(play.id)

        res_del = self.client.delete(url)
        res_put = self.client.put(url)

        self.assertEqual(res_del.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(res_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
