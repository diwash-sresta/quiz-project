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
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomSignUpForm  # Import your custom form

def signup_view(request):
    if request.method == 'POST':
        form = CustomSignUpForm(request.POST)  # Use CustomSignUpForm instead
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('quiz_menu')
    else:
        form = CustomSignUpForm()  # Use CustomSignUpForm for empty form too
    return render(request, 'registration/signup.html', {'form': form})

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
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if quiz has questions
    if quiz.questions.count() == 0:
        messages.warning(request, "This quiz has no questions.")
        return redirect('quiz_menu')
    
    # Clear any existing session data for this quiz
    keys_to_delete = [k for k in request.session.keys() if k.startswith(f'quiz_{quiz_id}')]
    for key in keys_to_delete:
        del request.session[key]
    
    # Initialize quiz session data
    request.session[f'quiz_{quiz_id}_score'] = 0
    request.session[f'quiz_{quiz_id}_questions_answered'] = []
    
    first_question = quiz.questions.first()
    if first_question:
        return redirect('quiz_question', quiz_id=quiz.id, question_id=first_question.id)
    else:
        messages.warning(request, "This quiz has no questions.")
        return redirect('quiz_menu')


@login_required(login_url='/login/')
@login_required(login_url='/login/')
def quiz_question(request, quiz_id, question_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    question = get_object_or_404(Question, id=question_id, quiz=quiz)

    # Get or initialize the question start time
    question_start_time_key = f'quiz_{quiz_id}_question_{question_id}_start_time'
    question_start_time = request.session.get(question_start_time_key)
    
    if not question_start_time:
        # First time viewing this question, set start time
        question_start_time = timezone.now().isoformat()
        request.session[question_start_time_key] = question_start_time
    
    # Convert stored ISO format time back to datetime
    question_start_time = timezone.datetime.fromisoformat(question_start_time)
    
    # Get time limit using the new method
    time_limit = timedelta(seconds=question.get_time_limit())
    time_left = time_limit - (timezone.now() - question_start_time)

    if time_left.total_seconds() <= 0:
        # Time's up for this question
        questions_answered = request.session.get(f'quiz_{quiz_id}_questions_answered', [])
        if question_id not in questions_answered:
            questions_answered.append(question_id)
            request.session[f'quiz_{quiz_id}_questions_answered'] = questions_answered
            
            # Only create UserSubmission if one doesn't exist
            if not UserSubmission.objects.filter(
                user=request.user,
                quiz=quiz,
                question=question
            ).exists():
                # Create a UserSubmission for timeout (no answer selected)
                UserSubmission.objects.create(
                    user=request.user,
                    quiz=quiz,
                    question=question,
                    selected_choice=question.choices.first(),  # Select first choice as default for timeout
                    is_correct=False
                )
        
        messages.warning(request, "Time's up for this question!")
        
        # Get next question based on order
        next_question = quiz.questions.filter(
            order__gt=question.order
        ).order_by('order', 'id').first()

        if not next_question:
            # Fallback: Find the next question by ID
            next_question = quiz.questions.filter(
                id__gt=question.id
            ).order_by('id').first()
        
        if next_question:
            # Clear the current question's start time from session
            del request.session[question_start_time_key]
            return redirect('quiz_question', quiz_id=quiz_id, question_id=next_question.id)
        else:
            return finish_quiz(request, quiz_id)

    next_question = quiz.questions.filter(
        order__gt=question.order
    ).order_by('order', 'id').first()

    if not next_question:
        # Fallback: Find the next question by ID
        next_question = quiz.questions.filter(
            id__gt=question.id
        ).order_by('id').first()
    
    answered_questions = request.session.get(f'quiz_{quiz_id}_questions_answered', [])
    current_score = request.session.get(f'quiz_{quiz_id}_score', 0)

    # Debugging statements
    print(f"Current question ID: {question.id}, Order: {question.order}")
    print(f"Next question: {next_question}")
    print(f"Questions answered: {answered_questions}")

    context = {
        'quiz': quiz,
        'question': question,
        'next_question_id': next_question.id if next_question else None,
        'time_left': int(time_left.total_seconds()),
        'current_score': current_score,
        'questions_answered': len(answered_questions),
        'total_questions': quiz.questions.count(),
    }
    return render(request, 'quiz_question.html', context)
@login_required(login_url='/login/')
def submit_answer(request, quiz_id, question_id):
    if request.method != 'POST':
        return redirect('quiz_question', quiz_id=quiz_id, question_id=question_id)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    question = get_object_or_404(Question, id=question_id, quiz=quiz)
    
    # Check if the question time limit has expired
    question_start_time_key = f'quiz_{quiz_id}_question_{question_id}_start_time'
    question_start_time = request.session.get(question_start_time_key)
    
    if question_start_time:
        start_time = timezone.datetime.fromisoformat(question_start_time)
        time_limit = timedelta(seconds=question.get_time_limit())
        time_left = time_limit - (timezone.now() - start_time)
        
        if time_left.total_seconds() <= 0:
            messages.error(request, "Time's up! Your answer was not submitted.")
            return redirect('quiz_question', quiz_id=quiz_id, question_id=question_id)
    
    # Clear the question start time from session
    if question_start_time_key in request.session:
        del request.session[question_start_time_key]
    
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
    questions_answered = request.session.get(f'quiz_{quiz_id}_questions_answered', [])
    if question_id in questions_answered:
        messages.warning(request, "You have already answered this question.")
        return redirect('quiz_question', quiz_id=quiz_id, question_id=question_id)
    
    # Record answer and update score
    current_score = request.session.get(f'quiz_{quiz_id}_score', 0)
    if choice.is_correct:
        current_score += 1
        request.session[f'quiz_{quiz_id}_score'] = current_score
    
    questions_answered.append(question_id)
    request.session[f'quiz_{quiz_id}_questions_answered'] = questions_answered
    
    # Create or update UserSubmission
    UserSubmission.objects.update_or_create(
        user=request.user,
        quiz=quiz,
        question=question,
        defaults={
            'selected_choice': choice,
            'is_correct': choice.is_correct
        }
    )
    
    # Determine next question or finish quiz
    next_question = quiz.questions.filter(
        order__gt=question.order
    ).order_by('order', 'id').first()
    
    if not next_question:
        return finish_quiz(request, quiz_id)
    
    return redirect('quiz_question', quiz_id=quiz_id, question_id=next_question.id)

@login_required(login_url='/login/')
def finish_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    final_score = request.session.get(f'quiz_{quiz_id}_score', 0)

    # Create or update Result
    result, created = Result.objects.update_or_create(
        user=request.user,
        quiz=quiz,
        defaults={
            'score': final_score,
            'completion_time': timezone.now()
        }
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

    submissions = UserSubmission.objects.filter(user=request.user, quiz=quiz).order_by('created_at')

    context = {
        'quiz': quiz,
        'result': result,
        'score': result.score,
        'total_questions': total_questions,
        'percentage': round(percentage, 1),
        'submissions': submissions,
        'passing_score': quiz.passing_score,
        'passed': percentage >= quiz.passing_score if quiz.passing_score is not None else None,
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