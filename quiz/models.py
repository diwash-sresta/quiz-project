from django.db import models
from django.contrib.auth.models import User

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name="choices", on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class UserSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField(default=0)  # Set default value here
    submitted_at = models.DateTimeField(auto_now_add=True)

    def calculate_score(self, user_answers):
        """Automatically calculates the user's score based on answers."""
        correct_answers = 0
        total_questions = self.quiz.questions.count()

        for question in self.quiz.questions.all():
            correct_choice = Choice.objects.filter(question=question, is_correct=True).first()
            if correct_choice and user_answers.get(question.id) == correct_choice.id:
                correct_answers += 1

        self.score = correct_answers
        self.total_questions = total_questions

    def save(self, *args, **kwargs):
        """Override save to calculate the score before saving."""
        if hasattr(self, 'user_answers'):
            self.calculate_score(self.user_answers)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.quiz.title} - Score: {self.score}"

class Result(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)  # Allow anonymous users
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.quiz.title} ({self.score}/{self.total_questions})"
