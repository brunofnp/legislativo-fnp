from django import forms
from django.utils.text import slugify

from apps.comentarios.models import Comentario, Participacao
from apps.usuarios.models import Municipio, Perfil, Usuario


def salvar_municipio_perfil(perfil, nome, uf):
    """Cria/reaproveita o Município (por nome+UF) e associa ao Perfil.
    Vários usuários podem apontar para o mesmo município (ver Perfil.municipio)."""
    if not nome or not uf:
        return
    uf = uf.upper()
    municipio, _ = Municipio.objects.get_or_create(
        nome=nome,
        uf=uf,
        defaults={'slug': slugify(f'{nome}-{uf}')},
    )
    perfil.municipio = municipio


class CustomSignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label='Nome',
        widget=forms.TextInput(attrs={'placeholder': 'Seu nome'}),
    )
    last_name = forms.CharField(
        max_length=150,
        label='Sobrenome',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Seu sobrenome'}),
    )
    municipio = forms.CharField(
        max_length=255,
        label='Município',
        widget=forms.TextInput(attrs={'placeholder': 'Seu município'}),
    )
    uf = forms.CharField(
        max_length=2,
        label='UF',
        widget=forms.TextInput(attrs={'placeholder': 'UF', 'maxlength': 2, 'class': 'uppercase'}),
    )
    setor_responsavel = forms.CharField(
        max_length=255,
        label='Setor responsável',
        widget=forms.TextInput(attrs={'placeholder': 'Ex.: Gabinete, Secretaria de Educação...'}),
    )
    cargo = forms.CharField(
        max_length=255,
        label='Cargo',
        widget=forms.TextInput(attrs={'placeholder': 'Seu cargo'}),
    )
    telefone = forms.CharField(
        max_length=32,
        label='Telefone',
        widget=forms.TextInput(attrs={'placeholder': 'Seu telefone'}),
    )

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.save()

        perfil = user.perfil
        perfil.setor_responsavel = self.cleaned_data['setor_responsavel']
        perfil.cargo = self.cleaned_data['cargo']
        perfil.telefone = self.cleaned_data['telefone']
        salvar_municipio_perfil(perfil, self.cleaned_data['municipio'], self.cleaned_data['uf'])
        perfil.save()


class PerfilForm(forms.ModelForm):
    """Dados nativos de autenticação (Usuario). Ver PerfilDadosForm para os campos de Perfil."""

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-wide'}),
            'last_name': forms.TextInput(attrs={'class': 'input-wide'}),
        }


class PerfilDadosForm(forms.ModelForm):
    municipio_nome = forms.CharField(
        max_length=255,
        label='Município',
        required=False,
        widget=forms.TextInput(attrs={'class': 'input-wide'}),
    )
    municipio_uf = forms.CharField(
        max_length=2,
        label='UF',
        required=False,
        widget=forms.TextInput(attrs={'class': 'input-wide uppercase', 'maxlength': 2}),
    )

    class Meta:
        model = Perfil
        fields = ['foto', 'telefone', 'cargo', 'setor_responsavel']
        labels = {
            'foto': 'Foto de perfil',
            'telefone': 'Telefone',
            'cargo': 'Cargo',
            'setor_responsavel': 'Setor responsável',
        }
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'input-wide'}),
            'cargo': forms.TextInput(attrs={'class': 'input-wide'}),
            'setor_responsavel': forms.TextInput(attrs={'class': 'input-wide'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.municipio_id:
            self.fields['municipio_nome'].initial = self.instance.municipio.nome
            self.fields['municipio_uf'].initial = self.instance.municipio.uf

    def save(self, commit=True):
        perfil = super().save(commit=False)
        salvar_municipio_perfil(perfil, self.cleaned_data.get('municipio_nome'), self.cleaned_data.get('municipio_uf'))
        if commit:
            perfil.save()
        return perfil


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto', 'parent']
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 4, 'class': 'input-wide'}),
            'parent': forms.HiddenInput(),
        }
        labels = {
            'texto': 'Comentário',
        }


class ParticipacaoForm(forms.ModelForm):
    class Meta:
        model = Participacao
        fields = [
            'tipo',
            'municipio',
            'uf',
            'proposicao',
            'setor_responsavel',
            'cargo',
            'email',
            'telefone',
            'mensagem',
        ]
        widgets = {
            'mensagem': forms.Textarea(attrs={'rows': 4, 'class': 'input-wide'}),
            'tipo': forms.HiddenInput(),
            'proposicao': forms.HiddenInput(),
            'municipio': forms.TextInput(attrs={'class': 'input-wide'}),
            'uf': forms.TextInput(attrs={'class': 'input-wide uppercase', 'maxlength': 2}),
            'setor_responsavel': forms.TextInput(attrs={'class': 'input-wide'}),
            'cargo': forms.TextInput(attrs={'class': 'input-wide'}),
            'email': forms.EmailInput(attrs={'class': 'input-wide'}),
            'telefone': forms.TextInput(attrs={'class': 'input-wide'}),
        }
        labels = {
            'mensagem': 'Mensagem',
            'uf': 'UF',
            'setor_responsavel': 'Setor responsável',
            'proposicao': 'Proposição',
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        municipio = cleaned_data.get('municipio')
        email = cleaned_data.get('email')
        setor_responsavel = cleaned_data.get('setor_responsavel')
        mensagem = cleaned_data.get('mensagem')

        if not municipio:
            raise forms.ValidationError('Município é obrigatório.')
        if not setor_responsavel:
            raise forms.ValidationError('Setor responsável é obrigatório.')
        if not email:
            raise forms.ValidationError('E-mail é obrigatório.')

        if tipo == Participacao.Tipo.SUGESTAO or tipo == Participacao.Tipo.INDICACAO or tipo == Participacao.Tipo.DUVIDA:
            if not cleaned_data.get('proposicao'):
                raise forms.ValidationError('Proposição é obrigatória para esta participação.')
            if not mensagem:
                raise forms.ValidationError('Explique seu motivo ou dúvida.')
        return cleaned_data
