from django.urls import path
from . import views

urlpatterns = [
    # Main Quiz Navigation
    path('', views.quiz_menu_view, name='quiz_menu'),
    path('list/', views.quiz_list_view, name='quiz_list'),
    
    # Quiz Taking Flow
    path('<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('<int:quiz_id>/question/<int:question_id>/', views.quiz_question, name='quiz_question'),
    path('<int:quiz_id>/question/<int:question_id>/submit/', views.submit_answer, name='submit_answer'),
    path('<int:quiz_id>/finish/', views.finish_quiz, name='finish_quiz'),
    path('<int:quiz_id>/result/<int:result_id>/', views.quiz_result, name='quiz_result'),
    
    # User Profile and History
    path('profile/', views.user_profile, name='user_profile'),
    path('history/', views.quiz_history, name='quiz_history'),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
]