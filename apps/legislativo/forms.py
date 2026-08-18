from django import forms
from django.conf import settings
from django.utils.text import slugify

from apps.comentarios.models import Comentario
from apps.proposicoes.models import AnexoProposicao
from apps.usuarios.models import Municipio, Perfil, Usuario

CLASSE_USUARIO_SIGNUP_CHOICES = [
    (valor, rotulo) for valor, rotulo in Perfil.CLASSE_USUARIO_CHOICES if valor != Perfil.EQUIPE_FNP
]


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
    classe_usuario = forms.ChoiceField(
        choices=CLASSE_USUARIO_SIGNUP_CHOICES,
        label='Você é',
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
        widget=forms.TextInput(attrs={'placeholder': 'Seu telefone', 'type': 'tel'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campo só existe se RECAPTCHA_PUBLIC_KEY/RECAPTCHA_PRIVATE_KEY
        # estiverem configuradas (ver settings.py) -- sem chave real, o
        # cadastro continua exatamente como antes, sem captcha nenhum
        # (nunca usa as chaves de teste do Google, que sempre validam e
        # não protegem nada de verdade).
        if getattr(settings, 'RECAPTCHA_HABILITADO', False):
            from django_recaptcha.fields import ReCaptchaField
            from django_recaptcha.widgets import ReCaptchaV2Checkbox

            self.fields['captcha'] = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.save()

        perfil = user.perfil
        perfil.classe_usuario = self.cleaned_data['classe_usuario']
        perfil.setor_responsavel = self.cleaned_data['setor_responsavel']
        perfil.cargo = self.cleaned_data['cargo']
        perfil.telefone = self.cleaned_data['telefone']
        salvar_municipio_perfil(perfil, self.cleaned_data['municipio'], self.cleaned_data['uf'])
        perfil.save()


class PerfilForm(forms.ModelForm):
    """Dados nativos de autenticação (Usuario). Ver PerfilDadosForm para os campos de Perfil."""

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-wide'}),
            'last_name': forms.TextInput(attrs={'class': 'input-wide'}),
            'email': forms.EmailInput(attrs={'class': 'input-wide'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        ja_existe = Usuario.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists()
        if ja_existe:
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        email_mudou = 'email' in self.changed_data
        if commit:
            usuario.save()
            if email_mudou:
                # allauth guarda o e-mail também em EmailAddress (verificação,
                # e-mail primário) -- sem sincronizar aqui, ficaria desatualizado
                # mesmo com o login por e-mail já funcionando via Usuario.email.
                from allauth.account.models import EmailAddress

                EmailAddress.objects.filter(user=usuario).delete()
                EmailAddress.objects.create(user=usuario, email=usuario.email, primary=True, verified=False)
        return usuario


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
        fields = ['foto', 'classe_usuario', 'telefone', 'cargo', 'setor_responsavel']
        labels = {
            'foto': 'Foto de perfil',
            'classe_usuario': 'Você é',
            'telefone': 'Telefone',
            'cargo': 'Cargo',
            'setor_responsavel': 'Setor responsável',
        }
        widgets = {
            'classe_usuario': forms.Select(attrs={'class': 'input-wide'}),
            'telefone': forms.TextInput(attrs={'class': 'input-wide', 'type': 'tel'}),
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

    def __init__(self, *args, proposicao=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Sem restringir o queryset aqui, "parent" (campo escondido, setado
        # via JS ao clicar em "Responder") aceitava o pk de um comentário de
        # QUALQUER proposição -- um POST manual conseguia encaixar uma
        # resposta na árvore de comentários de uma proposição diferente da
        # que o formulário realmente pertence (auditoria de segurança,
        # 2026-08-11). Sem proposição informada, nenhum parent é aceito.
        self.fields['parent'].queryset = (
            Comentario.objects.filter(proposicao=proposicao) if proposicao else Comentario.objects.none()
        )


class AnexoProposicaoForm(forms.ModelForm):
    class Meta:
        model = AnexoProposicao
        fields = ['arquivo', 'titulo']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Título do documento (opcional)'}),
        }
        labels = {
            'arquivo': 'Arquivo',
            'titulo': 'Título',
        }


