import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FormTest(TestCase):

    CREATE_POST_IN_BASE = 1
    NOT_CREATE_POST_IN_BASE = 0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="NoName")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test_slug",
            description="Описание тестовой группы",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.autorized_client = Client()
        self.autorized_client.force_login(FormTest.user)
        self.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        self.uploaded = SimpleUploadedFile(
            name="small.gif", content=self.small_gif, content_type="image/gif"
        )
        self.form = {
            "text": "Новый тестовый пост",
            "author": FormTest.user,
            "group": self.group.id,
            "image": self.uploaded,
        }  # Добавить в форму поле картинки

    def correct_fields_post(self, post):
        """Проверка полей формы поста."""
        fields = (
            (post.author, FormTest.user),
            (post.group, FormTest.group),
            (post.text, self.form["text"]),
            (post.image.size, self.form["image"].size),
        )  # Добавить поле для проверки картинки
        return fields

    # Добавить тест картинки здесь
    def test_create_post_is_valid_form(self):
        """Создан новый пост при передаче валидной формы."""
        response = self.autorized_client.post(
            reverse("posts:post_create"),
            self.form,
        )
        new_post = Post.objects.get(id=1)
        correct_fields = self.correct_fields_post(new_post)
        for post_fields, test_fields in correct_fields:
            with self.subTest(post_fields=post_fields):
                self.assertEqual(post_fields, test_fields)
        self.assertEqual(Post.objects.all().count(), self.CREATE_POST_IN_BASE)
        self.assertRedirects(
            response,
            f"/profile/{new_post.author}/",
            HTTPStatus.FOUND,
            HTTPStatus.OK,
        )

    def test_not_create_post_not_authorized_client(self):
        """Неавторизованный пользователь не может создать пост."""
        response = self.client.post(reverse("posts:post_create"), self.form)
        posts_count = Post.objects.count()
        self.assertEqual(posts_count, self.NOT_CREATE_POST_IN_BASE)
        self.assertRedirects(
            response,
            "/auth/login/?next=/create/",
            HTTPStatus.FOUND,
            HTTPStatus.OK,
        )

    def test_edit_post_is_valid_form(self):
        """При отправке валидной формы пост редактируется, новый не создан."""
        post = Post.objects.create(
            text="Пост для редактирования",
            author=FormTest.user,
        )
        posts_count = Post.objects.count()
        posts_group_count = FormTest.group.posts.count()
        self.autorized_client.post(
            reverse("posts:post_edit", args=[post.id]), self.form
        )
        post_edit = Post.objects.get(id=post.id)
        posts_count_after_edit = Post.objects.count()
        posts_group_count_after_edit = FormTest.group.posts.count()
        correct_fields = self.correct_fields_post(post_edit)
        for post_fields, test_fields in correct_fields:
            with self.subTest(post_fields=post_fields):
                self.assertEqual(post_fields, test_fields)
        self.assertEqual(posts_count, posts_count_after_edit)
        self.assertEqual(
            posts_group_count + self.CREATE_POST_IN_BASE, posts_group_count_after_edit
        )
