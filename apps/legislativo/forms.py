from django import forms

from .models import Comentario, Participacao, Usuario


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

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.save()


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'telefone', 'cargo']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'telefone': 'Telefone',
            'cargo': 'Cargo',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-wide'}),
            'last_name': forms.TextInput(attrs={'class': 'input-wide'}),
            'telefone': forms.TextInput(attrs={'class': 'input-wide'}),
            'cargo': forms.TextInput(attrs={'class': 'input-wide'}),
        }


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
            'responsavel',
            'cargo',
            'email',
            'whatsapp',
            'mensagem',
        ]
        widgets = {
            'mensagem': forms.Textarea(attrs={'rows': 4, 'class': 'input-wide'}),
            'tipo': forms.HiddenInput(),
            'proposicao': forms.HiddenInput(),
            'municipio': forms.TextInput(attrs={'class': 'input-wide'}),
            'uf': forms.TextInput(attrs={'class': 'input-wide uppercase', 'maxlength': 2}),
            'responsavel': forms.TextInput(attrs={'class': 'input-wide'}),
            'cargo': forms.TextInput(attrs={'class': 'input-wide'}),
            'email': forms.EmailInput(attrs={'class': 'input-wide'}),
            'whatsapp': forms.TextInput(attrs={'class': 'input-wide'}),
        }
        labels = {
            'mensagem': 'Mensagem',
            'uf': 'UF',
            'responsavel': 'Responsável',
            'proposicao': 'Proposição',
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        municipio = cleaned_data.get('municipio')
        email = cleaned_data.get('email')
        responsavel = cleaned_data.get('responsavel')
        mensagem = cleaned_data.get('mensagem')

        if not municipio:
            raise forms.ValidationError('Município é obrigatório.')
        if not responsavel:
            raise forms.ValidationError('Responsável é obrigatório.')
        if not email:
            raise forms.ValidationError('E-mail é obrigatório.')

        if tipo == Participacao.Tipo.SUGESTAO or tipo == Participacao.Tipo.INDICACAO or tipo == Participacao.Tipo.DUVIDA:
            if not cleaned_data.get('proposicao'):
                raise forms.ValidationError('Proposição é obrigatória para esta participação.')
            if not mensagem:
                raise forms.ValidationError('Explique seu motivo ou dúvida.')
        return cleaned_data
