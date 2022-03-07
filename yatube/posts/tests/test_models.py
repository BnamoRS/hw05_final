from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="auth")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="grouptest",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="просто тестовый пост",
        )

    def test_models_have_correct_objects_names_post(self):
        """Проверяем, что у модели корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        models_str = {
            post: post.text[:15],
            group: group.title,
        }
        for model_str, expected_value in models_str.items():
            with self.subTest():
                self.assertEqual(
                    model_str.__str__(),
                    expected_value,
                )
