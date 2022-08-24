import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='hasnoname')
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа №1',
            slug='test-slug',
            description='Описание тестовой группы №1'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый текст поста'
        )
        cls.posts_num = 12
        cls.post_per_page = 10

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user_client = Client()
        self.user_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        pages_names_templates = {
            reverse('posts:index'):
            'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.author.username}):
            'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
            ('posts/post_detail.html'),
            reverse('posts:post_create'):
            'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
            'posts/create_post.html'
        }
        for reverse_name, template in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_homepage_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        page_obj_context = response.context['page_obj'].object_list
        posts = list(Post.objects.select_related(
            'group', 'author').all()[:self.post_per_page])
        self.assertEqual(posts, page_obj_context)

    def test_group_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        page_obj = list(self.group.posts.select_related('group',
                        'author').all()[:self.post_per_page])
        response = self.guest_client.get(reverse('posts:group_list',
                                         kwargs={'slug': self.group.slug}))
        group_context = response.context['group']
        page_obj_context = response.context['page_obj'].object_list
        self.assertEqual(group_context, self.group)
        self.assertEqual(page_obj_context, page_obj)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        author = self.author
        posts_count = author.posts.select_related('author').count()
        following = Follow.objects.filter(user=self.user,
                                          author=author).exists()
        page_obj = list(author.posts.select_related('author')[:10])
        response = self.user_client.get(reverse('posts:profile',
                                        kwargs={'username': author.username}))
        author_context = response.context['author']
        posts_count_context = response.context['posts_count']
        following_context = response.context['following']
        page_obj_context = response.context['page_obj'].object_list
        self.assertEqual(author_context, author)
        self.assertEqual(posts_count_context, posts_count)
        self.assertEqual(following_context, following)
        self.assertEqual(page_obj_context, page_obj)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:post_detail',
                                         kwargs={'post_id': self.post.id}))
        post_context = response.context['post']
        self.assertEqual(post_context, self.post)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:post_edit',
                                          kwargs={'post_id': (self.post.id)}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.user_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_correct_location(self):
        """Пост появляется в нужных разделах"""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new-group',
            description='Описание новой группы'
        )
        test_post = Post.objects.create(
            author=self.author,
            group=new_group,
            text='Пост для проверки расположения'
        )
        response = self.guest_client.get(reverse('posts:index'))
        page_obj_context = response.context['page_obj'].object_list
        self.assertIn(test_post, page_obj_context)
        response = self.guest_client.get(reverse('posts:profile',
                                         kwargs={'username':
                                                 (test_post.author.username)}))
        page_obj_context = response.context['page_obj'].object_list
        self.assertIn(test_post, page_obj_context)
        response = self.guest_client.get(reverse('posts:group_list',
                                         kwargs={'slug':
                                                 (test_post.group.slug)}))
        page_obj_context = response.context['page_obj'].object_list
        self.assertIn(test_post, page_obj_context)
        response = self.guest_client.get(reverse('posts:group_list',
                                         kwargs={'slug': self.group.slug}))
        page_obj_context = response.context['page_obj'].object_list
        self.assertNotIn(test_post, page_obj_context)

    def test_paginator(self):
        """Тестирование пагинатора"""
        posts = [Post(text=f'Пост № {post_num}',
                      author=self.author,
                      group=self.group)
                 for post_num in range(self.posts_num)]
        Post.objects.bulk_create(posts)
        urls_with_paginator = ('/',
                               f'/group/{self.group.slug}/',
                               f'/profile/{self.author.username}/')
        page_posts = ((1, 10), (2, 3))
        for url_address in urls_with_paginator:
            for page, posts_count in page_posts:
                response = self.guest_client.get(url_address, {"page": page})
                page_obj_context = response.context['page_obj'].object_list
                with self.subTest():
                    self.assertEqual(len(page_obj_context), posts_count)

    def test_post_with_image(self):
        """Изображение передается в словаре context"""
        small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                     b'\x01\x00\x80\x00\x00\x00\x00\x00'
                     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                     b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(name='small.gif',
                                      content=small_gif,
                                      content_type='image/gif')
        post_gif = Post.objects.create(author=self.author,
                                       group=self.group,
                                       text='Тестовый текст поста',
                                       image=uploaded)
        response = self.guest_client.get(reverse('posts:post_detail',
                                         kwargs={'post_id': post_gif.id}))
        post_context = response.context['post']
        self.assertEqual(post_context, post_gif)
        url_kwargs = {'posts:index': {},
                      'posts:group_list': {'slug': post_gif.group.slug},
                      'posts:profile': {'username':
                                        (post_gif.author.username)}}
        for url, kwargs in url_kwargs.items():
            with self.subTest():
                response = self.guest_client.get(reverse(url, kwargs=kwargs))
                page_obj_context = response.context['page_obj'].object_list
                self.assertIn(post_gif, page_obj_context)

    def test_user_creates_comment(self):
        """Авторизованный пользователь может оставить комментарий"""
        user_text = 'Пользовательский комментарий'
        comments_count_before = self.post.comments.count()
        self.user_client.post(reverse('posts:add_comment',
                                      kwargs={'post_id': self.post.id}),
                              data={'text': user_text},
                              follow=True)
        self.assertEqual(comments_count_before + 1, self.post.comments.count())
        self.assertTrue(self.post.comments.filter(text=user_text).exists())

    def test_guest_creates_comment(self):
        """Гость не может оставить комментарий"""
        guest_text = 'Гостевой комментарий'
        comments_count_before = self.post.comments.count()
        self.guest_client.post(reverse('posts:add_comment',
                                       kwargs={'post_id': self.post.id}),
                               data={'text': guest_text},
                               follow=True)
        self.assertEqual(comments_count_before, self.post.comments.count())
        self.assertFalse(self.post.comments.filter(text=guest_text).exists())

    def test_comment_show_correct_context(self):
        """Комментарий появляется на странице поста"""
        comment_text = 'Пользовательский комментарий'
        self.user_client.post(reverse('posts:add_comment',
                                      kwargs={'post_id': self.post.id}),
                              data={'text': comment_text},
                              follow=True)
        response = self.user_client.get(reverse('posts:post_detail',
                                                kwargs={'post_id':
                                                        self.post.id}))
        comment = response.context['comments'].filter(text=comment_text)
        self.assertTrue(comment.exists())

    def test_cache_work_is_correct(self):
        """Тестирование кэширования"""
        post = Post.objects.create(author=self.author,
                                   group=self.group,
                                   text='Этот пост будет удален')
        after_create = self.guest_client.get(reverse('posts:index')).content
        post.delete()
        after_delete = self.guest_client.get(reverse('posts:index')).content
        cache.clear()
        after_clear = self.guest_client.get(reverse('posts:index')).content
        self.assertEqual(after_create, after_delete)
        self.assertNotEqual(after_create, after_clear)

    def test_subscribe(self):
        """Пользователь может подписываться"""
        self.user_client.post(reverse('posts:profile_follow',
                                      kwargs={'username':
                                              self.author.username}))
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.author).exists())

    def test_unsubscribe(self):
        """Пользователь может отписываться"""
        Follow.objects.create(user=self.user, author=self.author)
        self.user_client.post(reverse('posts:profile_unfollow',
                                      kwargs={'username':
                                              self.author.username}))
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.author).exists())

    def test_self_subscribe(self):
        """Пользователь не может подписаться на себя"""
        self.user_client.post(reverse('posts:profile_follow',
                                      kwargs={'username':
                                              self.user.username}))
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.user).exists())

    def test_subscriber_got_new_post(self):
        """Новый пост появляется у подписчиков"""
        Follow.objects.create(user=self.user, author=self.author)
        new_post = Post.objects.create(author=self.author,
                                       text='Новый пост автора')
        response = self.user_client.get(reverse('posts:follow_index'))
        page_obj_context = response.context['page_obj'].object_list
        self.assertIn(new_post, page_obj_context)

    def test_not_subscriber_didnt_got_new_post(self):
        """Новый пост не появляется у неподписанных пользователей"""
        new_post = Post.objects.create(author=self.author,
                                       text='Новый пост автора')
        response = self.user_client.get(reverse('posts:follow_index'))
        page_obj_context = response.context['page_obj'].object_list
        self.assertNotIn(new_post, page_obj_context)
