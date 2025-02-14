from django.contrib import admin
from .models import Quiz, Question, Choice, UserSubmission

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3  # Allow adding 3 choices by default

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz')  
    search_fields = ('text',)
    inlines = [ChoiceInline]  

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')  
    search_fields = ('title',)  
    list_filter = ('created_at',)  

class UserSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'total_questions', 'submitted_at')
    list_filter = ('quiz', 'score')
    search_fields = ('user__username', 'quiz__title')
    ordering = ['-submitted_at']  # New line to order submissions by most recent


# ✅ Register models only ONCE
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(UserSubmission, UserSubmissionAdmin)
