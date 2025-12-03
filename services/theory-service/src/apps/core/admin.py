from django.contrib import admin
from .models import Course, Lesson, Quiz, Question, StudentProgress, ExamAttempt


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'course_type', 'status', 'duration_hours', 'price']
    list_filter = ['course_type', 'status']
    search_fields = ['code', 'title', 'description']
    ordering = ['code']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'lesson_type', 'is_published', 'is_mandatory']
    list_filter = ['lesson_type', 'is_published', 'is_mandatory']
    search_fields = ['title', 'description']
    ordering = ['course', 'order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'quiz_type', 'passing_score', 'time_limit_minutes', 'is_published']
    list_filter = ['quiz_type', 'is_published']
    search_fields = ['title', 'description']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'order', 'question_type', 'points']
    list_filter = ['question_type']
    search_fields = ['question_text']
    ordering = ['quiz', 'order']


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'course', 'lesson', 'status', 'progress_percentage', 'last_accessed']
    list_filter = ['status']
    search_fields = ['student_id']
    ordering = ['-last_accessed']


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'quiz', 'attempt_number', 'status', 'score', 'passed', 'submitted_at']
    list_filter = ['status', 'passed']
    search_fields = ['student_id']
    ordering = ['-started_at']
