from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Painel Root — Legislativo FNP'
admin.site.site_title = 'Legislativo FNP'
admin.site.index_title = 'Administração e hierarquia de acesso'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('contas/', include('allauth.urls')),
    path('', include('apps.legislativo.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
