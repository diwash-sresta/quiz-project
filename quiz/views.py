from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Quiz, Question, Choice, UserSubmission, Result
from django.contrib import messages
from django.db.models import Avg
# Authentication Views
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('quiz_menu')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    def get_success_url(self):
        return resolve_url('quiz_menu')

class CustomLogoutView(LogoutView):
    next_page = 'login'

from django.shortcuts import render
from .models import Quiz, Result

def quiz_menu_view(request):
    quizzes = Quiz.objects.all()
    user_results = {}

    if request.user.is_authenticated:
        for quiz in quizzes:
            try:
                user_results[quiz.id] = Result.objects.filter(quiz=quiz, user=request.user).latest('completion_time')
            except Result.DoesNotExist:
                user_results[quiz.id] = None  # No result exists for this quiz

    return render(request, 'quiz_menu.html', {'quizzes': quizzes, 'user_results': user_results})

# Quiz Taking Views
@login_required(login_url='/login/')
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if quiz has questions
    if quiz.questions.count() == 0:
        messages.warning(request, "This quiz has no questions.")
        return redirect('quiz_menu')
    
    # Check if user has any ongoing quiz
    if any(key.startswith('quiz_') for key in request.session.keys()):
        messages.warning(request, "You have an ongoing quiz. Please complete it first.")
        return redirect('quiz_menu')
    
    # Initialize quiz session data
    request.session[f'quiz_{quiz_id}_score'] = 0
    request.session[f'quiz_{quiz_id}_start_time'] = timezone.now().isoformat()
    request.session[f'quiz_{quiz_id}_time_limit'] = quiz.time_limit or 600  # Default 10 minutes
    request.session[f'quiz_{quiz_id}_questions_answered'] = []
    
    first_question = quiz.questions.first()
    if first_question:
        return redirect('quiz_question', quiz_id=quiz.id, question_id=first_question.id)
    else:
        messages.warning(request, "This quiz has no questions.")
        return redirect('quiz_menu')

@login_required(login_url='/login/')
def quiz_question(request, quiz_id, question_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    question = get_object_or_404(Question, id=question_id, quiz=quiz)
    
    # Verify quiz is in progress
    start_time = request.session.get(f'quiz_{quiz_id}_start_time')
    if not start_time:
        messages.error(request, "Quiz session has expired or was not properly started.")
        return redirect('quiz_menu')
    
    # Calculate time remaining
    start_time = timezone.datetime.fromisoformat(start_time)
    time_limit = timedelta(seconds=request.session.get(f'quiz_{quiz_id}_time_limit', 600))
    time_left = time_limit - (timezone.now() - start_time)
    
    if time_left.total_seconds() <= 0:
        messages.warning(request, "Time's up!")
        return finish_quiz(request, quiz_id)
    
    # Get next question
    next_question = quiz.questions.filter(id__gt=question.id).first()
    questions_answered = request.session.get(f'quiz_{quiz_id}_questions_answered', [])
    current_score = request.session.get(f'quiz_{quiz_id}_score', 0)
    
    context = {
        'quiz': quiz,
        'question': question,
        'next_question_id': next_question.id if next_question else None,  # Handle case where next_question is None
        'time_left': int(time_left.total_seconds()),
        'current_score': current_score,
        'questions_answered': len(questions_answered),
        'total_questions': quiz.questions.count(),
    }
    return render(request, 'quiz_question.html', context)
@login_required(login_url='/login/')
@login_required(login_url='/login/')
def submit_answer(request, quiz_id, question_id):
    if request.method != 'POST':
        return redirect('quiz_question', quiz_id=quiz_id, question_id=question_id)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    question = get_object_or_404(Question, id=question_id, quiz=quiz)
    
    # Verify quiz is in progress and time hasn't expired
    start_time = request.session.get(f'quiz_{quiz_id}_start_time')
    if not start_time:
        messages.error(request, "Quiz session has expired.")
        return redirect('quiz_menu')
    
    choice_id = request.POST.get('choice')
    if not choice_id:
        messages.warning(request, "Please select an answer.")
        return redirect('quiz_question', quiz_id=quiz_id, question_id=question_id)
    
    try:
        choice = Choice.objects.get(id=choice_id, question=question)
    except Choice.DoesNotExist:
        messages.error(request, "Invalid choice selected.")
        return redirect('quiz_question', quiz_id=quiz_id, question_id=question_id)
    
    # Check if the user has already submitted an answer for this question
    existing_submission = UserSubmission.objects.filter(
        user=request.user,
        quiz=quiz,
        question=question
    ).first()
    
    if existing_submission:
        # Update the existing submission
        existing_submission.selected_choice = choice
        existing_submission.is_correct = choice.is_correct
        existing_submission.save()
    else:
        # Record answer and update score
        questions_answered = request.session.get(f'quiz_{quiz_id}_questions_answered', [])
        if question_id not in questions_answered:
            current_score = request.session.get(f'quiz_{quiz_id}_score', 0)
            if choice.is_correct:
                current_score += 1
                request.session[f'quiz_{quiz_id}_score'] = current_score
            
            questions_answered.append(question_id)
            request.session[f'quiz_{quiz_id}_questions_answered'] = questions_answered
            
            UserSubmission.objects.create(
                user=request.user,
                quiz=quiz,
                question=question,
                selected_choice=choice,
                is_correct=choice.is_correct
            )
    
    # Determine next question or finish quiz
    next_question = quiz.questions.filter(id__gt=question.id).first()
    if not next_question:
        return finish_quiz(request, quiz_id)
    
    return redirect('quiz_question', quiz_id=quiz_id, question_id=next_question.id)

@login_required(login_url='/login/')
def finish_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Get final score and create result
    final_score = request.session.get(f'quiz_{quiz_id}_score', 0)
    result = Result.objects.create(
        user=request.user,
        quiz=quiz,
        score=final_score,
        completion_time=timezone.now()
    )
    
    # Clear quiz session data
    keys_to_delete = [k for k in request.session.keys() if k.startswith(f'quiz_{quiz_id}')]
    for key in keys_to_delete:
        del request.session[key]
    
    return redirect('quiz_result', quiz_id=quiz_id, result_id=result.id)

@login_required(login_url='/login/')
def quiz_result(request, quiz_id, result_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    result = get_object_or_404(Result, id=result_id, user=request.user, quiz=quiz)
    
    total_questions = quiz.questions.count()
    percentage = (result.score / total_questions * 100) if total_questions > 0 else 0
    
    # Get user's submissions for this quiz
    submissions = UserSubmission.objects.filter(
        user=request.user,
        quiz=quiz,
        created_at__gte=result.completion_time - timedelta(hours=1)
    ).order_by('created_at')
    
    context = {
        'quiz': quiz,
        'result': result,
        'score': result.score,
        'total_questions': total_questions,
        'percentage': round(percentage, 1),
        'submissions': submissions,
        'passing_score': quiz.passing_score,
        'passed': percentage >= quiz.passing_score if quiz.passing_score else None,
    }
    return render(request, 'quiz_result.html', context)

# User Profile and History Views
@login_required(login_url='/login/')
def user_profile(request):
    user_results = Result.objects.filter(user=request.user).order_by('-completion_time')
    completed_quizzes = Quiz.objects.filter(result__user=request.user).distinct()
    
    context = {
        'user': request.user,
        'results': user_results,
        'completed_quizzes': completed_quizzes,
        'total_quizzes_taken': user_results.count(),
        'average_score': user_results.aggregate(Avg('score'))['score__avg']
    }
    return render(request, 'user_profile.html', context)

@login_required(login_url='/login/')
def quiz_history(request):
    user_submissions = UserSubmission.objects.filter(user=request.user).order_by('-created_at')
    results = Result.objects.filter(user=request.user).order_by('-completion_time')
    
    context = {
        'submissions': user_submissions,
        'results': results
    }
    return render(request, 'quiz_history.html', context)