from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("create_user", views.create_user, name="create_user"),
    path("main", views.main, name="main"),
    path("mod_chat", views.mod_chat, name="mod_chat"),
    path("hilos", views.hilos, name="hilos"),
    path("mod_hilos", views.mod_hilos, name="mod_hilos"),
    path("mensajes", views.mensajes, name="mensajes"),
    path("chatsbots", views.chatsbots, name="chatsbots"),
    path("chat/<str:tipo>/", views.chatbot_view, name="chatbot_view"),
    path("log_out/", views.log_out, name="log_out"),
    path("CB_academico/", lambda r: views.chatbot_view(r, "academico"), name="CB_academico"),
    path("CB_utilidad/", lambda r: views.chatbot_view(r, "utilidad"), name="CB_utilidad"),
    path("CB_calculo/", lambda r: views.chatbot_view(r, "calculo"), name="CB_calculo"),
    path("CB_wikipedia/", lambda r: views.chatbot_view(r, "wikipedia"), name="CB_wikipedia"),
    path("CB_programacion/", lambda r: views.chatbot_view(r, "programacion"), name="CB_programacion"),

]
