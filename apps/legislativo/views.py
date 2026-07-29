import json

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_GET

from .forms import ComentarioForm, ParticipacaoForm
from .models import Macrotema, Participacao, Proposicao


def get_filtered_proposicoes(query, macrotema_slug):
    proposicoes = Proposicao.objects.select_related('macrotema', 'tema').all()
    if macrotema_slug:
        proposicoes = proposicoes.filter(macrotema__slug=macrotema_slug)
    if query:
        proposicoes = proposicoes.filter(
            Q(titulo__icontains=query)
            | Q(ementa_resumida__icontains=query)
            | Q(status_tramitacao__icontains=query)
            | Q(local__icontains=query)
            | Q(tema__nome__icontains=query)
            | Q(macrotema__nome__icontains=query)
        )
    return proposicoes


class HomeView(View):
    template_name = 'legislativo/home.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        macrotema_slug = request.GET.get('macrotema', '').strip()
        macrotemas = Macrotema.objects.order_by('nome')

        filtered = get_filtered_proposicoes(query, macrotema_slug)
        stats = {
            'total': filtered.count(),
            'pauta': filtered.filter(pauta=True).count(),
            'urgentes': filtered.filter(urgente=True).count(),
            'alta_prioridade': filtered.filter(prioridade_fnp='alta').count(),
        }

        proposicoes = filtered.order_by('-urgente', '-pauta', '-aprovada', 'parada', 'prioridade_fnp', '-criado_em')[:100]

        return render(
            request,
            self.template_name,
            {
                'proposicoes': proposicoes,
                'macrotemas': macrotemas,
                'active_macrotema': macrotema_slug,
                'query': query,
                'stats': stats,
            },
        )


@require_GET
def api_proposicoes(request):
    query = request.GET.get('q', '').strip()
    macrotema_slug = request.GET.get('macrotema', '').strip()
    proposicoes = get_filtered_proposicoes(query, macrotema_slug)

    counts = {
        'total': proposicoes.count(),
        'pauta': proposicoes.filter(pauta=True).count(),
        'urgentes': proposicoes.filter(urgente=True).count(),
        'alta_prioridade': proposicoes.filter(prioridade_fnp='alta').count(),
    }

    return JsonResponse({'counts': counts})


@require_GET
def api_proposicao_detail(request, pk):
    proposicao = get_object_or_404(Proposicao, pk=pk)
    data = {
        'id': proposicao.pk,
        'titulo': proposicao.titulo,
        'casa': proposicao.get_casa_display() if hasattr(proposicao, 'get_casa_display') else proposicao.casa,
        'status_tramitacao': proposicao.status_tramitacao,
        'macrotema': {
            'nome': proposicao.macrotema.nome if proposicao.macrotema else None,
            'cor': proposicao.macrotema.cor if proposicao.macrotema else None,
        },
        'prioridade_fnp': proposicao.get_prioridade_fnp_display(),
        'urgente': proposicao.urgente,
        'aprovada': proposicao.aprovada,
        'pauta': proposicao.pauta,
        'tema': proposicao.tema.nome if proposicao.tema else None,
        'ementa_resumida': proposicao.ementa_resumida,
        'proximos_eventos': proposicao.proximos_eventos,
        'interlocutores': proposicao.interlocutores,
        'ultima_movimentacao': proposicao.ultima_movimentacao,
        'posicionamento_fnp': proposicao.posicionamento_fnp,
        'acoes_incidencia': proposicao.acoes_incidencia,
        'riscos_oportunidades': proposicao.riscos_oportunidades,
    }
    return JsonResponse(data)


@require_GET
def api_proposicao_sse(request):
    response = HttpResponse(content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'

    query = request.GET.get('q', '').strip()
    macrotema_slug = request.GET.get('macrotema', '').strip()
    proposicoes = get_filtered_proposicoes(query, macrotema_slug)

    counts = {
        'total': proposicoes.count(),
        'pauta': proposicoes.filter(pauta=True).count(),
        'urgentes': proposicoes.filter(urgente=True).count(),
        'alta_prioridade': proposicoes.filter(prioridade_fnp='alta').count(),
    }
    response.write(f'data: {json.dumps({"counts": counts})}\n\n')
    return response


class ProposicaoDetailView(View):
    template_name = 'legislativo/proposicao_detail.html'

    def get(self, request, pk):
        proposicao = get_object_or_404(Proposicao, pk=pk)
        comentarios = proposicao.comentarios.filter(parent__isnull=True, status_moderacao='aprovado').select_related('autor')
        comentario_form = ComentarioForm(initial={'parent': None})
        participacao_form = ParticipacaoForm(initial={'proposicao': proposicao.titulo, 'tipo': 'sugestao'})
        return render(
            request,
            self.template_name,
            {
                'proposicao': proposicao,
                'comentarios': comentarios,
                'comentario_form': comentario_form,
                'participacao_form': participacao_form,
            },
        )

    def post(self, request, pk):
        proposicao = get_object_or_404(Proposicao, pk=pk)
        form_type = request.POST.get('form_type')
        comentario_form = ComentarioForm(initial={'parent': None})
        participacao_form = ParticipacaoForm(initial={'proposicao': proposicao.titulo, 'tipo': 'sugestao'})
        success_message = None

        if form_type == 'comentario':
            comentario_form = ComentarioForm(request.POST)
            if comentario_form.is_valid():
                comentario = comentario_form.save(commit=False)
                comentario.proposicao = proposicao
                comentario.save()
                return redirect('legislativo:proposicao_detail', pk=pk)
        else:
            participacao_form = ParticipacaoForm(request.POST)
            if participacao_form.is_valid():
                participacao_form.save()
                success_message = 'Sua contribuição foi registrada com sucesso.'

        comentarios = proposicao.comentarios.filter(parent__isnull=True, status_moderacao='aprovado').select_related('autor')
        return render(
            request,
            self.template_name,
            {
                'proposicao': proposicao,
                'comentarios': comentarios,
                'comentario_form': comentario_form,
                'participacao_form': participacao_form,
                'success_message': success_message,
            },
        )


class ParticipacaoListView(View):
    template_name = 'legislativo/participacao_list.html'

    def get(self, request):
        participacoes = Participacao.objects.all()[:100]
        return render(request, self.template_name, {'participacoes': participacoes})
