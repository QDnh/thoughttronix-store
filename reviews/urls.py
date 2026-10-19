from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("reviews/create/<int:pk>/", views.ReviewCreateView.as_view(), name="create"),
    path("reviews/<int:pk>/edit/", views.ReviewEditView.as_view(), name="edit"),
    path("reviews/<int:pk>/cancel/", views.ReviewCancelView.as_view(), name="cancel"),
    path("reviews/<int:pk>/update/", views.ReviewUpdateView.as_view(), name="update"),
    path("reviews/<int:pk>/delete/", views.ReviewDeleteView.as_view(), name="delete"),
]
