from django.contrib import admin
from .models import TrainingProgram, Syllabus, Stage, Lesson, StudentEnrollment, LessonCompletion, StageCheck

@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'program_type', 'min_flight_hours', 'is_active']
    list_filter = ['program_type', 'is_active']

@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ['name', 'program', 'version', 'is_active']

@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ['name', 'syllabus', 'order']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'stage', 'lesson_type', 'order']
    list_filter = ['lesson_type']

@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'program', 'status', 'enrolled_at']
    list_filter = ['status']

@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'lesson', 'grade', 'completed_at']

@admin.register(StageCheck)
class StageCheckAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'stage', 'result', 'scheduled_at']
