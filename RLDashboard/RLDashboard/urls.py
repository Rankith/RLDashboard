"""
Definition of urls for RLDashboard.
"""

from django.conf.urls import include, url
import Main.views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    url(r'^$', Main.views.index, name='index'),
    url(r'^home$', Main.views.index, name='home'),
    url(r'^checkreplay$', Main.views.checkreplay, name='checkreplay'),
    url(r'^getreplay', Main.views.getreplay, name='getreplay'),
    # Examples:
    # url(r'^$', RLDashboard.views.home, name='home'),
    # url(r'^RLDashboard/', include('RLDashboard.RLDashboard.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
]
