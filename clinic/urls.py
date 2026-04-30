"""
URL configuration for clinic project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

handler403 = "clinic.views.error_403"
handler404 = "clinic.views.error_404"
handler500 = "clinic.views.error_500"

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('admin-panel/', include('dashboard.urls')),
    path('api/', include('scheduling.api.urls')),
    path('accounts/', include('accounts.urls')),
    path('queueing/', include('queueing.urls')),
    path('emr/', include('emr.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('scheduling/', include('scheduling.urls')),
    path('notifications/', include('notifications.urls')),
]
