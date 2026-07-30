import json
import time

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Max, Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from .forms import ComentarioForm, ParticipacaoForm, PerfilForm
from .models import Notificacao, Participacao, Proposicao, Tema

FAVORITOS_SESSION_KEY = 'favoritos'
RECENTES_SESSION_KEY = 'recentes'
RECENTES_MAX = 8


def get_favoritos_ids(request):
    return set(request.session.get(FAVORITOS_SESSION_KEY, []))


def get_recentes_ids(request):
    return request.session.get(RECENTES_SESSION_KEY, [])


def notificar_participantes_da_discussao(proposicao, comentario):
    participantes_ids = (
        proposicao.comentarios
        .exclude(autor__isnull=True)
        .exclude(autor=comentario.autor)
        .values_list('autor_id', flat=True)
        .distinct()
    )
    Notificacao.objects.bulk_create(
        Notificacao(
            destinatario_id=destinatario_id,
            proposicao=proposicao,
            comentario=comentario,
            mensagem=f'Novo comentário de {comentario.autor} em "{proposicao.titulo}"',
        )
        for destinatario_id in participantes_ids
    )


def registrar_visualizacao(request, proposicao):
    Proposicao.objects.filter(pk=proposicao.pk).update(visualizacoes=F('visualizacoes') + 1)
    recentes = [pk for pk in get_recentes_ids(request) if pk != proposicao.pk]
    recentes.insert(0, proposicao.pk)
    request.session[RECENTES_SESSION_KEY] = recentes[:RECENTES_MAX]


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

        base = Proposicao.objects.select_related('macrotema').prefetch_related('temas')

        urgentes = base.filter(urgente=True).order_by('-criado_em')[:6]

        em_alta = (
            base.annotate(
                comentarios_count=Count(
                    'comentarios', distinct=True, filter=Q(comentarios__status_moderacao='aprovado')
                )
            )
            .annotate(relevancia=F('visualizacoes') + F('comentarios_count') * 5)
            .filter(Q(visualizacoes__gt=0) | Q(comentarios_count__gt=0))
            .order_by('-relevancia')[:4]
        )

        recentes_ids = get_recentes_ids(request)
        recentes_map = {p.pk: p for p in base.filter(pk__in=recentes_ids)}
        recentes = [recentes_map[pk] for pk in recentes_ids if pk in recentes_map]

        areas_interesse = Tema.objects.filter(proposicoes__pk__in=recentes_ids).distinct()[:8] if recentes_ids else []
        if not areas_interesse:
            areas_interesse = Tema.objects.annotate(num=Count('proposicoes')).filter(num__gt=0).order_by('-num')[:8]

        return render(
            request,
            self.template_name,
            {
                'proposicoes': proposicoes,
                'urgentes': urgentes,
                'em_alta': em_alta,
                'recentes': recentes,
                'areas_interesse': areas_interesse,
                'temas': temas,
                'active_tema': tema_slug,
                'active_tema_obj': active_tema_obj,
                'query': query,
                'stats': stats,
                'favoritos_ids': get_favoritos_ids(request),
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


@require_POST
def toggle_favorito(request, pk):
    proposicao = get_object_or_404(Proposicao, pk=pk)
    favoritos = request.session.get(FAVORITOS_SESSION_KEY, [])
    if proposicao.pk in favoritos:
        favoritos.remove(proposicao.pk)
    else:
        favoritos.append(proposicao.pk)
    request.session[FAVORITOS_SESSION_KEY] = favoritos

    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('legislativo:home')


class FavoritosListView(View):
    template_name = 'legislativo/favoritos_list.html'

    def get(self, request):
        favoritos_ids = get_favoritos_ids(request)
        favoritos_map = {
            p.pk: p
            for p in Proposicao.objects.select_related('macrotema').prefetch_related('temas').filter(pk__in=favoritos_ids)
        }
        proposicoes = [favoritos_map[pk] for pk in favoritos_ids if pk in favoritos_map]
        return render(
            request,
            self.template_name,
            {
                'proposicoes': proposicoes,
                'favoritos_ids': favoritos_ids,
                'page_title': 'Favoritos',
            },
        )


@login_required
def ler_notificacao(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, destinatario=request.user)
    notificacao.lida = True
    notificacao.save(update_fields=['lida'])
    return redirect('legislativo:proposicao_detail', pk=notificacao.proposicao_id)


@login_required
@require_POST
def marcar_notificacoes_lidas(request):
    request.user.notificacoes.filter(lida=False).update(lida=True)
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('legislativo:home')


class ProposicaoDetailView(View):
    template_name = 'legislativo/proposicao_detail.html'

    def get(self, request, pk):
        proposicao = get_object_or_404(Proposicao, pk=pk)
        registrar_visualizacao(request, proposicao)
        comentarios = proposicao.comentarios.filter(parent__isnull=True, status_moderacao='aprovado').select_related('autor')
        comentario_form = ComentarioForm(initial={'parent': None})
        participacao_form = ParticipacaoForm(initial={'proposicao': proposicao.titulo, 'tipo': 'sugestao'})
        return render(
            request,
            self.template_name,
            {
                'proposicao': proposicao,
                'page_title': proposicao.titulo,
                'comentarios': comentarios,
                'comentario_form': comentario_form,
                'favoritos_ids': get_favoritos_ids(request),
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
                if request.user.is_authenticated:
                    comentario.autor = request.user
                comentario.save()
                if comentario.autor_id:
                    notificar_participantes_da_discussao(proposicao, comentario)
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
                'page_title': proposicao.titulo,
                'comentarios': comentarios,
                'comentario_form': comentario_form,
                'favoritos_ids': get_favoritos_ids(request),
                'participacao_form': participacao_form,
                'success_message': success_message,
            },
        )


class ParticipacaoListView(View):
    template_name = 'legislativo/participacao_list.html'

    def get(self, request):
        participacoes = Participacao.objects.all()[:100]
        return render(request, self.template_name, {'participacoes': participacoes, 'page_title': 'Participações'})


class PerfilView(View):
    template_name = 'legislativo/perfil.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = PerfilForm(instance=request.user)
        return self._render(request, form)

    def post(self, request):
        form = PerfilForm(request.POST, instance=request.user)
        success_message = None
        if form.is_valid():
            form.save()
            success_message = 'Perfil atualizado com sucesso.'
        return self._render(request, form, success_message)

    def _render(self, request, form, success_message=None):
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'success_message': success_message,
                'page_title': 'Meu perfil',
                'mostrar_sidebar': True,
            },
        )
