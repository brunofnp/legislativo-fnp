from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.usuarios.views import definir_senha_social

urlpatterns = [
    path('admin/', admin.site.urls),
    # Precisa vir antes do include('allauth.urls') -- mesmo path/nome que
    # account_set_password, pra sobrescrever a view nativa (ver docstring
    # de definir_senha_social).
    path('contas/password/set/', definir_senha_social, name='account_set_password'),
    path('contas/', include('allauth.urls')),
    path('', include('apps.legislativo.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
