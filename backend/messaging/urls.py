from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("encounters/<str:encounter_id>/chat/", views.ChatView.as_view(), name="chat"),
    path("encounters/<str:encounter_id>/chat/messages/", views.SendMessageView.as_view(),
         name="send"),
    path("encounters/<str:encounter_id>/chat/close/", views.CloseChatView.as_view(),
         name="close"),
]
