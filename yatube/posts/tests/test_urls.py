from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class URLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_post = User.objects.create_user(username='HasNoNameAuthor')
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_test',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.author_post,
            text='Тестовый пост',
            id=33,
        )
        cls.public_urls = (
            ('/', 'posts/index.html'),
            (f'/group/{cls.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{cls.author_post.username}/', 'posts/profile.html'),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html'),
        )
        cls.not_public_urls = (
            (f'/posts/{cls.post.id}/edit/',
                'posts/create_post.html',
                f'/posts/{cls.post.id}/'),
            ('/create/',
                'posts/create_post.html',
                '/auth/login/?next=/create/'),
        )
        cls.unexisting_url = '/unexisting_page/'
        cls.name_url_comments = (
            f'/posts/{cls.post.id}/comment/',
            'posts/post_detail.html',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.author_post_client = Client()
        self.authorized_client.force_login(URLTest.user)
        self.author_post_client.force_login(URLTest.author_post)

    def test_public_urls_for_guest_client_ok(self):
        """Публичные страницы доступны неавторизированному пользователю."""
        for url, _ in URLTest.public_urls:
            response = self.guest_client.get(url)
            with self.subTest(url=url):
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_not_public_urls_for_guest_client_found(self):
        """Непубличные страницы не доступны
        неавторизированному пользователю.
        """
        for url, _, _ in URLTest.not_public_urls:
            response = self.guest_client.get(url)
            with self.subTest(url=url):
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_public_urls_for_authorized_client(self):
        """Публичные страницы доступны авторизированному пользователю."""
        for url, _ in URLTest.public_urls:
            response = self.authorized_client.get(url)
            with self.subTest(url=url):
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_and_edit_post_urls_for_author_post_client(self):
        """Создание и редактирование поста доступно автору."""
        for url, _, _ in URLTest.not_public_urls:
            with self.subTest(url=url):
                response = self.author_post_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post_urls_for_authorized_client(self):
        """Редактирование поста недоступно авторизированному пользователю."""
        response = self.authorized_client.get(URLTest.not_public_urls[0][0])
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unexisting_url(self):
        """Тестирование несуществующей страницы."""
        response = self.guest_client.get(URLTest.unexisting_url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_template_public_urls_guest(self):
        """Тестирование публичных страниц неавторизованным пользователем."""
        for url, template in URLTest.public_urls:
            response = self.guest_client.get(url)
            with self.subTest(url=url):
                self.assertTemplateUsed(response, template)

    def test_template_not_public_urls_guest(self):
        """Тестирование непубличных страниц неавторизованным пользователем."""
        for url, _, url_redirect in URLTest.not_public_urls:
            response = self.guest_client.get(url)
            with self.subTest(url=url):
                self.assertRedirects(
                    response,
                    url_redirect,
                    HTTPStatus.FOUND,
                    HTTPStatus.OK
                )

    def test_template_public_urls_authorized_client(self):
        """Тестирование публичных страниц авторизованным пользователем."""
        for url, template in URLTest.public_urls:
            response = self.authorized_client.get(url)
            with self.subTest(url=url):
                self.assertTemplateUsed(response, template)

    def test_template_create_post(self):
        """Тестирование шаблона создания поста."""
        response = self.authorized_client.get(URLTest.not_public_urls[1][0])
        self.assertTemplateUsed(response, URLTest.not_public_urls[1][1])

    def test_template_edit_post_authorized_client(self):
        """Тестирование шаблона редактирования поста авторизированным
        пользователем.
        """
        response = self.authorized_client.get(URLTest.not_public_urls[0][0])
        self.assertRedirects(
            response,
            URLTest.public_urls[3][0],
            HTTPStatus.FOUND,
            HTTPStatus.OK,
        )

    def test_template_edit_post_author(self):
        """Тестирование шаблона редактирования поста автором."""
        response = self.author_post_client.get(URLTest.not_public_urls[0][0])
        self.assertTemplateUsed(response, URLTest.not_public_urls[0][1])

    def test_template_comment_post_guest_client(self):
        """Проверка шаблона комментария для гостя."""
        response = self.guest_client.get(URLTest.name_url_comments[0])
        post_id = URLTest.post.id
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{post_id}/comment/',
            HTTPStatus.FOUND,
            HTTPStatus.OK,
        )

    def test_template_comment_post_authorized_client(self):
        """Проверка шаблона комментария для авторизированного пользователя."""
        response = self.authorized_client.get(URLTest.name_url_comments[0])
        post_id = URLTest.post.id
        self.assertRedirects(
            response,
            f'/posts/{post_id}/',
            HTTPStatus.FOUND,
            HTTPStatus.OK,
        )
