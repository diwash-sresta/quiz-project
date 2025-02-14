from django.urls import path
from . import views

urlpatterns = [
    path('', views.quiz_menu_view, name='quiz_menu'),
    path('list/', views.quiz_list, name='quiz_list'),  # ✅ Changed to "list/" for clarity
    path('<int:quiz_id>/detail/', views.quiz_detail, name='quiz_detail'),  # ✅ Added "detail/"
    path('<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('<int:quiz_id>/result/<int:score>/', views.quiz_result, name='quiz_result'),

    # Authentication URLs
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
]
