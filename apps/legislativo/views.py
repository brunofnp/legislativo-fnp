import json
import time

from django.db.models import Max, Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_GET

from .forms import ComentarioForm, ParticipacaoForm
from .models import Participacao, Proposicao, Tema


def get_filtered_proposicoes(query, tema_slug):
    proposicoes = Proposicao.objects.select_related('macrotema').prefetch_related('temas').all()
    if tema_slug:
        proposicoes = proposicoes.filter(temas__slug=tema_slug)
    if query:
        proposicoes = proposicoes.filter(
            Q(titulo__icontains=query)
            | Q(ementa_resumida__icontains=query)
            | Q(status_tramitacao__icontains=query)
            | Q(local__icontains=query)
            | Q(temas__nome__icontains=query)
            | Q(macrotema__nome__icontains=query)
        )
    if tema_slug or query:
        proposicoes = proposicoes.distinct()
    return proposicoes


class HomeView(View):
    template_name = 'legislativo/home.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        tema_slug = request.GET.get('tema', '').strip()
        temas = Tema.objects.order_by('nome')
        active_tema_obj = temas.filter(slug=tema_slug).first() if tema_slug else None

        filtered = get_filtered_proposicoes(query, tema_slug)
        stats = compute_counts(filtered)

        proposicoes = filtered.order_by('-urgente', '-pauta', '-aprovada', 'parada', 'prioridade_fnp', '-criado_em')[:100]

        return render(
            request,
            self.template_name,
            {
                'proposicoes': proposicoes,
                'temas': temas,
                'active_tema': tema_slug,
                'active_tema_obj': active_tema_obj,
                'query': query,
                'stats': stats,
            },
        )


def compute_counts(proposicoes):
    return {
        'total': proposicoes.count(),
        'pauta': proposicoes.filter(pauta=True).count(),
        'urgentes': proposicoes.filter(urgente=True).count(),
        'alta_prioridade': proposicoes.filter(prioridade_fnp='alta').count(),
        'com_relator': proposicoes.filter(interlocutores__icontains='relator').count(),
    }


@require_GET
def api_proposicoes(request):
    query = request.GET.get('q', '').strip()
    tema_slug = request.GET.get('tema', '').strip()
    proposicoes = get_filtered_proposicoes(query, tema_slug)
    return JsonResponse({'counts': compute_counts(proposicoes)})


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
        'temas': [tema.nome for tema in proposicao.temas.all()],
        'ementa_resumida': proposicao.ementa_resumida,
        'proximos_eventos': proposicao.proximos_eventos,
        'interlocutores': proposicao.interlocutores,
        'ultima_movimentacao': proposicao.ultima_movimentacao,
        'posicionamento_fnp': proposicao.posicionamento_fnp,
        'acoes_incidencia': proposicao.acoes_incidencia,
        'riscos_oportunidades': proposicao.riscos_oportunidades,
    }
    return JsonResponse(data)


SSE_POLL_INTERVAL_SECONDS = 5
SSE_MAX_ITERATIONS = 120  # ~10 min por conexão; o EventSource do navegador reconecta sozinho


def _sse_stream(query, tema_slug):
    last_snapshot = None
    for _ in range(SSE_MAX_ITERATIONS):
        proposicoes = get_filtered_proposicoes(query, tema_slug)
        latest = proposicoes.aggregate(Max('atualizado_em'))['atualizado_em__max']
        counts = compute_counts(proposicoes)
        snapshot = (latest, tuple(sorted(counts.items())))

        if snapshot != last_snapshot:
            payload = {'counts': counts, 'updated': last_snapshot is not None}
            yield f'data: {json.dumps(payload, default=str)}\n\n'
            last_snapshot = snapshot
        else:
            yield ': heartbeat\n\n'

        time.sleep(SSE_POLL_INTERVAL_SECONDS)


@require_GET
def api_proposicao_sse(request):
    query = request.GET.get('q', '').strip()
    tema_slug = request.GET.get('tema', '').strip()

    response = StreamingHttpResponse(
        _sse_stream(query, tema_slug),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
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
