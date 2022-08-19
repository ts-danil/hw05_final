import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа №1',
            slug='test-slug',
            description='Описание тестовой группы №1'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_post_create_adds_item_in_database(self):
        """ Проверка сохранения новых постов из формы """
        posts_count_before = Post.objects.count()
        form_data = {
            'text': 'Текст из формы',
            'group': self.group.id
        }
        self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        posts_count_after = Post.objects.count()
        self.assertEqual(posts_count_before + 1, posts_count_after)
        self.assertTrue(Post.objects.filter(
                        text=form_data['text'],
                        group=form_data['group']).exists())

    def test_post_edit_changes_item_in_database(self):
        """ Проверка редактирования существующих постов из формы """
        post = Post.objects.create(
            author=self.author,
            group=self.group,
            text='Старый текст'
        )
        form_data = {
            "group": self.group.id,
            'text': 'Новый текст из формы'
        }
        self.author_client.post(
            reverse('posts:post_edit', args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertTrue(Post.objects.filter(
                        id=post.id,
                        group=form_data['group'],
                        text=form_data['text']).exists())

    def test_post_with_img_create_adds_item_in_database(self):
        """ Проверка сохранения новых постов с изображением из формы """
        posts_count_before = Post.objects.count()
        small_img = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                     b'\x01\x00\x80\x00\x00\x00\x00\x00'
                     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                     b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(name='small.jpg',
                                      content=small_img,
                                      content_type='image/jpg')
        form_data = {'text': 'Текст из формы',
                     'group': self.group.id,
                     'image': uploaded}
        self.author_client.post(reverse('posts:post_create'),
                                data=form_data,
                                follow=True)
        self.assertEqual(posts_count_before + 1, Post.objects.count())
        self.assertTrue(Post.objects.filter(text=form_data['text'],
                                            group=form_data['group'],
                                            image='posts/small.jpg').exists())
