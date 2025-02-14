from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.shortcuts import resolve_url
from .models import Quiz, Question, Choice, UserSubmission,Result
from django.urls import reverse 

# 🟢 View for listing all quizzes
def quiz_list(request):
    quizzes = Quiz.objects.all()
    return render(request, 'quiz_list.html', {'quizzes': quizzes})

# 🟢 View for displaying quiz details and questions
@login_required(login_url='/login/')  # Redirects to login page if not authenticated
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    top_scores = UserSubmission.objects.filter(quiz=quiz).order_by('-score')[:5]  
    return render(request, 'quiz_detail.html', {'quiz': quiz, 'questions': questions, 'top_scores': top_scores})

# 🟢 View to submit a quiz and calculate the score
@login_required(login_url='/login/')
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == 'POST':
        score = 0
        total_questions = quiz.questions.count()
        user_answers = []

        for question in quiz.questions.all():
            choice_id = request.POST.get(str(question.id))
            if choice_id:
                choice = get_object_or_404(Choice, id=choice_id)
                if choice.is_correct:
                    score += 1
                user_answers.append(int(choice_id))

        # Save result automatically
        user_submission = UserSubmission.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            total_questions=total_questions
        )

        return redirect('quiz_result', quiz_id=quiz.id, score=score)

    return redirect('quiz_list')

# 🟢 View to display quiz results
@login_required(login_url='/login/')
def quiz_result(request, quiz_id, score):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    return render(request, 'quiz_result.html', {'quiz': quiz, 'score': score})



# 🟢 View for the quiz menu
def quiz_menu_view(request):
    quizzes = Quiz.objects.all()
    return render(request, "quiz_menu.html", {"quizzes": quizzes})

# 🟢 View for listing all quizzes (alternative)
def quiz_list_view(request):
    quizzes = Quiz.objects.all()
    return render(request, 'quiz/quiz_list.html', {'quizzes': quizzes})

# 🟢 User registration (signup) view
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('quiz_menu')  # Redirect to quiz menu after signup
    else:
        form = UserCreationForm()
    
    return render(request, 'signup.html', {'form': form})

# 🟢 User login view
class CustomLoginView(LoginView):
    def get_redirect_url(self):
        return resolve_url('quiz_menu')  # ✅ Ensures correct redirection

# 🟢 User logout view
class CustomLogoutView(LogoutView):
    next_page = 'login'  # ✅ Redirect to login page after logout
