from django.contrib import admin
from .models import Quiz, Question, Choice, UserSubmission, Result

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3
    fields = ('text', 'is_correct', 'explanation')
    can_delete = True

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ('text', 'order', 'explanation')
    show_change_link = True

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'order', 'get_correct_answer')
    list_filter = ('quiz',)
    search_fields = ('text', 'quiz__title')
    ordering = ('quiz', 'order', 'id')
    inlines = [ChoiceInline]
    
    def get_correct_answer(self, obj):
        correct = obj.choices.filter(is_correct=True).first()
        return correct.text if correct else "No correct answer set"
    get_correct_answer.short_description = 'Correct Answer'

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_question_count', 'time_limit', 'passing_score', 
                   'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
    inlines = [QuestionInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'is_active')
        }),
        ('Settings', {
            'fields': ('time_limit', 'passing_score'),
            'classes': ('collapse',)
        })
    )
    
    def get_question_count(self, obj):
        return obj.questions.count()
    get_question_count.short_description = 'Questions'

class UserSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'question', 'selected_choice', 
                   'is_correct', 'created_at')
    list_filter = ('quiz', 'is_correct', 'created_at')
    search_fields = ('user__username', 'quiz__title', 'question__text')
    ordering = ('-created_at',)
    readonly_fields = ('is_correct',)

    def has_add_permission(self, request):
        return False  # Prevent manual creation of submissions

class ResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'get_percentage', 'passed',
                   'completion_time', 'get_time_taken')
    list_filter = ('quiz', 'passed', 'completion_time')
    search_fields = ('user__username', 'quiz__title')
    ordering = ('-completion_time',)
    readonly_fields = ('passed',)
    
    def get_percentage(self, obj):
        return f"{obj.calculate_percentage():.1f}%"
    get_percentage.short_description = 'Score %'
    
    def get_time_taken(self, obj):
        if obj.time_taken:
            minutes = obj.time_taken.seconds // 60
            seconds = obj.time_taken.seconds % 60
            return f"{minutes}m {seconds}s"
        return "N/A"
    get_time_taken.short_description = 'Time Taken'

    def has_add_permission(self, request):
        return False  # Prevent manual creation of results

# Register all models
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(UserSubmission, UserSubmissionAdmin)
admin.site.register(Result, ResultAdmin)