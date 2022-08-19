from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='hasnoname')
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст поста'
        )

    def setUp(self):
        self.guest_client = Client()
        self.user_client = Client()
        self.user_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        cache.clear()

    def test_all_page_exists(self):
        """Проверка корректности кодов ответа для всех страниц"""
        url_client_status = (('/',
                             self.guest_client,
                             HTTPStatus.OK
                              ),
                             ('/unexisting_page/',
                             self.guest_client,
                             HTTPStatus.NOT_FOUND
                              ),
                             (f'/group/{self.group.slug}/',
                              self.guest_client,
                              HTTPStatus.OK
                              ),
                             (f'/profile/{self.author.username}/',
                              self.guest_client,
                              HTTPStatus.OK
                              ),
                             (f'/posts/{self.post.id}/',
                              self.guest_client,
                              HTTPStatus.OK
                              ),
                             ('/create/',
                              self.user_client,
                              HTTPStatus.OK
                              ),
                             (f'/posts/{self.post.id}/edit/',
                              self.author_client,
                              HTTPStatus.OK))

        for url, client, status in url_client_status:
            response = client.get(url)
            with self.subTest(status=status):
                self.assertEqual(response.status_code, status)

    def test_page_with_redirect(self):
        """Тестирование перенаправления"""
        url_client_redirect = (('/create/',
                                self.guest_client,
                                '/auth/login/'
                                ),
                               (f'/posts/{self.post.id}/edit/',
                                self.guest_client,
                                f'/posts/{self.post.id}/'
                                ),
                               (f'/posts/{self.post.id}/edit/',
                                self.user_client,
                                f'/posts/{self.post.id}/'
                                ))
        for url, client, redirect in url_client_redirect:
            response = client.get(url)
            with self.subTest(redirect=redirect):
                self.assertRedirects(response, redirect)

    def test_urls_uses_correct_template(self):
        """URL-адреса используют соответствующие шаблоны"""
        url_names_templates = {
            '/': 'posts/index.html',
            '/nonexist-page/': 'core/404.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
        }
        for address, template in url_names_templates.items():
            with self.subTest(adress=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)
        response = self.user_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')
        response = self.author_client.get(f'/posts/{self.post.id}/edit/')
        self.assertTemplateUsed(response, 'posts/create_post.html')
