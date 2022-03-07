import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTests(TestCase):
    POSTS_IN_PAGE_1_PAGINATOR = 10
    POSTS_IN_PAGE_2_PAGINATOR = 2
    POSTS_ALL = POSTS_IN_PAGE_1_PAGINATOR + POSTS_IN_PAGE_2_PAGINATOR
    ADD_POST_OR_COMMENT = 1
    POST_IN_BASE = 1
    POST_IN_INDEX = 1
    DELETE_POST = 1
    ADD_FOLLOWER = 1
    DELETE_FOLLOWER = 0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="Vasya")
        cls.follower_user = User.objects.create_user(username="Follower")
        cls.group_1 = Group.objects.create(
            title="Тестовая группа",
            slug="testslug",
            description="Описание тестовой группы",
        )
        cls.group_2 = Group.objects.create(
            title="Другая группа",
            slug="testtestslug",
            description="Описание другой группы",
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.uploaded = SimpleUploadedFile(
            name="small.gif", content=cls.small_gif, content_type="image/gif"
        )
        cls.post = Post.objects.create(
            text="Тестовый пост",
            author=cls.user,
            group=cls.group_1,
            image=cls.uploaded,
        )
        cls.name_urls_public_template = (
            (reverse("posts:index"), "posts/index.html"),
            (reverse("posts:group_list", args=[cls.post.group.slug]),
                "posts/group_list.html"),
            (reverse("posts:profile", args=[cls.post.author]),
                "posts/profile.html"),
            (reverse("posts:post_detail", args=[cls.post.id]),
                "posts/post_detail.html"),
        )
        cls.name_urls_not_public_template = (
            (reverse("posts:post_edit", args=[cls.post.id]),
                "posts/create_post.html"),
            (reverse("posts:post_create"), "posts/create_post.html"),
        )
        cls.name_urls_paginator_template = (
            (reverse("posts:index"), "posts/index.html"),
            (
                reverse("posts:group_list", args=[cls.post.group.slug]),
                "posts/group_list.html",
            ),
            (reverse("posts:profile", args=[cls.post.author]),
                "posts/profile.html"),
        )
        cls.name_url_comments = reverse(
            "posts:add_comment", args=[cls.post.id])
        cls.name_url_follow = (
            (reverse("posts:profile_follow", args=[cls.post.author]),
                cls.ADD_FOLLOWER),
            (reverse("posts:profile_unfollow", args=[cls.post.author]),
                cls.DELETE_FOLLOWER),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.autorized_user_client = Client()
        self.follower_user_client = Client()
        self.autorized_user_client.force_login(ViewsTests.user)
        self.follower_user_client.force_login(ViewsTests.follower_user)

    def fields_post_correct(self, response_post):
        """Проверка полей поста из контекста шаблона."""
        value_fields_post = (
            (response_post.text, ViewsTests.post.text),
            (response_post.author, ViewsTests.post.author),
            (response_post.group, ViewsTests.post.group),
            (response_post.image.size, ViewsTests.uploaded.size),
            (response_post.image.name, f"posts/{ViewsTests.uploaded.name}"),
        )
        return value_fields_post

    def test_unexisting_page(self):
        """Проверка шаблона несуществующей страницы"""
        url_unexisting = "/unexisting_page/"
        response = self.client.get(url_unexisting)
        self.assertTemplateUsed(response, "core/404.html")

    def test_correct_template_public_urls(self):
        """Проверка шаблонов <name> публичных страниц."""
        for url_name, template_url in ViewsTests.name_urls_public_template:
            with self.subTest(url_name=url_name):
                response = self.client.get(url_name)
                self.assertTemplateUsed(response, template_url)

    def test_correct_template_not_public_urls(self):
        """Проверка шаблонов <name>  не публичных страниц."""
        for url_name, template_url in ViewsTests.name_urls_not_public_template:
            with self.subTest(url_name=url_name):
                response = self.autorized_user_client.get((url_name))
                self.assertTemplateUsed(response, template_url)

    def test_correct_context_post_details(self):
        """Проверка контекста, переданного в шаблон 'post_detail'."""
        response = self.autorized_user_client.get(
            ViewsTests.name_urls_public_template[3][0]
        )
        response_post = response.context["post"]
        value_fields_post = self.fields_post_correct(response_post)
        for field, value in value_fields_post:
            with self.subTest(field=field):
                self.assertEqual(field, value)

    def test_correct_context_paginator_template(self):
        """Проверка контекста постов на:

        - стартовой странице,
        - странице группы,
        - странице профайла.

        """
        for url_name, _ in ViewsTests.name_urls_paginator_template:
            with self.subTest(url_name=url_name):
                response = self.autorized_user_client.get(url_name)
                response_post = response.context.get("page_obj")[0]
                value_fields_post = self.fields_post_correct(response_post)
                for field, value in value_fields_post:
                    with self.subTest(field=field):
                        self.assertEqual(field, value)

    def test_total_number_submitted_posts(self):
        """Общее количество переданных постов на:

        - стартовую страницу,
        - страницу группы,
        - страницу профайла.

        """
        pages = (
            (1, self.POSTS_IN_PAGE_1_PAGINATOR),
            (2, self.POSTS_IN_PAGE_2_PAGINATOR),
        )
        Post.objects.bulk_create(
            [
                Post(
                    text="Тестовый пост",
                    author=ViewsTests.user,
                    group=ViewsTests.group_1,
                )
            ]
            * (self.POSTS_ALL - Post.objects.count())
        )
        for page, count in pages:
            for url_name, _ in ViewsTests.name_urls_paginator_template:
                with self.subTest(url_name=url_name):
                    response = self.client.get(url_name, {"page": page})
                    self.assertEqual(
                        response.context["page_obj"].paginator.count,
                        self.POSTS_ALL
                    )
                    self.assertEqual(
                        len(response.context["page_obj"].object_list), count
                    )

    def test_add_new_post_in_your_group(self):
        """При создании поста он появляется

        - на стартовой странице,
        - на странице профайла пользователя,
        - на странице своей группы.

        """
        group = Group.objects.get(title=ViewsTests.group_1)
        author = User.objects.get(username="Vasya")
        posts_count = Post.objects.count()
        posts_profile_count = author.posts.count()
        posts_group_count = group.posts.count()
        Post.objects.create(
            text="Создаю новый пост",
            author=ViewsTests.user,
            group=group,
        )
        posts_count_add = Post.objects.count()
        posts_group_count_add = group.posts.count()
        posts_profile_count_add = author.posts.count()
        counts = (
            (posts_count, posts_count_add),
            (posts_group_count, posts_group_count_add),
            (posts_profile_count, posts_profile_count_add),
        )
        for count, count_add in counts:
            with self.subTest():
                self.assertEqual(count_add, count + self.ADD_POST_OR_COMMENT)

    def test_not_add_new_post_in_other_group(self):
        """При создании поста он не появляется в другой группе."""
        group_your = Group.objects.get(title=ViewsTests.group_1)
        group_other = Group.objects.get(title=ViewsTests.group_2)
        posts_group_other_count = group_other.posts.count()
        Post.objects.create(
            text="Создаю новый пост",
            author=ViewsTests.user,
            group=group_your,
        )
        self.assertEqual(group_other.posts.count(), posts_group_other_count)

    def test_comments_autorized_user(self):
        """Проверка комментирования поста авторизированным пользователем."""
        name_url_detail_add_comment = self.name_urls_public_template[3][0]
        count_comment = ViewsTests.post.comments.count()
        comment_text = {"text": "Создаем комментарий к посту"}
        self.autorized_user_client.post(self.name_url_comments, comment_text)
        response = self.autorized_user_client.get(name_url_detail_add_comment)
        response_comment_text = (
            response.context["comments"].get(text=comment_text["text"]).text
        )
        self.assertEqual(
            len(response.context["comments"]),
            count_comment + self.ADD_POST_OR_COMMENT
        )
        self.assertEqual(response_comment_text, comment_text["text"])

    def test_comment_not_authorized_user(self):
        """Проверка комментирования поста неавторизированным пользователем."""
        name_url_detail_add_comment = self.name_urls_public_template[3][0]
        count_comment = ViewsTests.post.comments.count()
        comment_text = {"text": "Создаем комментарий к посту"}
        self.client.post(self.name_url_comments, comment_text)
        response = self.client.get(name_url_detail_add_comment)
        post_id = response.context["post"].id
        self.assertEqual(len(response.context["comments"]), count_comment)
        self.assertRedirects(
            self.client.get(self.name_url_comments),
            f"/auth/login/?next=/posts/{post_id}/comment/",
            HTTPStatus.FOUND,
            HTTPStatus.OK,
        )

    def test_cache_index(self):
        """Тест кеширования главной страницы."""
        response = self.client.get(self.name_urls_public_template[0][0])
        posts_in_base_count = Post.objects.count()
        posts_in_index_cont = response.context["page_obj"].paginator.count
        Post.objects.get(id=ViewsTests.post.id).delete()
        posts_in_base_count_after_removal = Post.objects.count()
        posts_in_index_cont_after_removal = (
            response.context["page_obj"].paginator.count)
        response_after_removal = (
            self.client.get(self.name_urls_public_template[0][0]))
        posts_in_base_count_after_response = Post.objects.count()
        posts_in_index_cont_after_response = (
            response_after_removal.context["page_obj"].paginator.count)
        count_posts = (
            (posts_in_base_count, self.POST_IN_BASE),
            (posts_in_index_cont, self.POST_IN_INDEX),
            (posts_in_base_count_after_removal,
                self.POST_IN_BASE - self.DELETE_POST),
            (posts_in_index_cont_after_removal, self.POST_IN_INDEX),
            (posts_in_base_count_after_response,
                self.POST_IN_BASE - self.DELETE_POST),
            (posts_in_index_cont_after_response,
                self.POST_IN_INDEX - self.DELETE_POST),
        )
        for count, value in count_posts:
            with self.subTest(count=count):
                self.assertEqual(count, value)

    def test_follow_authorized_user(self):
        """Авторизированный пользователь может подписываться и отписываться."""
        for url_follow, follow in ViewsTests.name_url_follow:
            with self.subTest(url_follow=url_follow):
                self.follower_user_client.get(url_follow)
                self.assertEqual(Follow.objects.count(), follow)

    def test_post_add_in_follow(self):
        """Пост появляется в ленте подписчика."""
        self.follower_user_client.get(ViewsTests.name_url_follow[0][0])
        response = self.follower_user_client.get(reverse("posts:follow_index"))
        count_post_follow = len(response.context["page_obj"])
        Post.objects.create(
            text="Пост в подписке",
            author=ViewsTests.user,
            group=ViewsTests.group_1,
            image=ViewsTests.uploaded,
        )
        response_follower = self.follower_user_client.get(
            reverse("posts:follow_index"))
        self.assertEqual(
            len(response_follower.context["page_obj"]),
            count_post_follow + self.ADD_POST_OR_COMMENT,
        )

    def test_post_not_add_in_unfollow(self):
        """Пост не появляется в ленте не подписанного."""
        response = self.follower_user_client.get(reverse("posts:follow_index"))
        count_post_follow = len(response.context["page_obj"])
        Post.objects.create(
            text="Пост в подписке",
            author=ViewsTests.user,
            group=ViewsTests.group_1,
            image=ViewsTests.uploaded,
        )
        response_follower_after_add_post = self.follower_user_client.get(
            reverse("posts:follow_index")
        )
        self.assertEqual(
            len(response_follower_after_add_post.context["page_obj"]),
            count_post_follow
        )
