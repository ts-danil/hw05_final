from django.forms import FileInput, ModelForm, Select, Textarea

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {'text': 'Текст сообщения',
                  'group': 'Группа',
                  'image': 'Картинка'}
        widgets = {
            "text": Textarea(attrs={
                'class': 'form-control',
                'cols': '40',
                'rows': '10'
            }),
            "group": Select(attrs={
                'class': 'form-control'
            }),
            "image": FileInput(attrs={
                'class': 'form-control',
                'type': 'file',
                'accept': 'image/*'
            })
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = {'text'}
        widgets = {"text": Textarea(attrs={'class': 'form-control',
                                           'cols': '40',
                                           'rows': '10'})}
