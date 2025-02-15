from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    time_limit = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Time limit in seconds. Leave blank for no limit.",
        validators=[MinValueValidator(60)]  # Minimum 1 minute
    )
    passing_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Passing score percentage. Leave blank if no passing score is required."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return self.title

    def get_total_questions(self):
        return self.questions.count()

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    text = models.TextField()
    order = models.IntegerField(default=0)
    explanation = models.TextField(
        blank=True,
        help_text="Explanation to show after the question is answered"
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text

    def get_correct_choice(self):
        return self.choices.filter(is_correct=True).first()

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name="choices", on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField(
        blank=True,
        help_text="Explanation for why this choice is correct/incorrect"
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.text

    def save(self, *args, **kwargs):
        # Ensure only one correct choice per question
        if self.is_correct:
            self.question.choices.exclude(id=self.id).update(is_correct=False)
        super().save(*args, **kwargs)

class UserSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        unique_together = ['user', 'quiz', 'question']  # Prevent multiple submissions for same question

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - Q{self.question.id}"

    def save(self, *args, **kwargs):
        # Automatically set is_correct based on selected choice
        self.is_correct = self.selected_choice.is_correct
        super().save(*args, **kwargs)

class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    completion_time = models.DateTimeField()
    time_taken = models.DurationField(
        null=True,
        blank=True,
        help_text="Time taken to complete the quiz"
    )
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ['-completion_time']
        unique_together = ['user', 'quiz', 'completion_time']  # Allow multiple attempts but not at same time

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.score}/{self.quiz.get_total_questions()})"

    def save(self, *args, **kwargs):
        # Calculate if passed based on quiz passing_score
        if self.quiz.passing_score is not None:
            total_questions = self.quiz.get_total_questions()
            if total_questions > 0:
                percentage = (self.score / total_questions) * 100
                self.passed = percentage >= self.quiz.passing_score
        super().save(*args, **kwargs)

    def calculate_percentage(self):
        total_questions = self.quiz.get_total_questions()
        if total_questions > 0:
            return (self.score / total_questions) * 100
        return 0