import { Routes } from '@angular/router';

export const trainingRoutes: Routes = [
  {
    path: '',
    children: [
      {
        path: '',
        redirectTo: 'syllabus',
        pathMatch: 'full',
      },
      {
        path: 'syllabus',
        loadComponent: () =>
          import('./features/syllabus/syllabus-list.component').then(
            (m) => m.SyllabusListComponent
          ),
      },
      {
        path: 'syllabus/:id',
        loadComponent: () =>
          import('./features/syllabus/syllabus-detail.component').then(
            (m) => m.SyllabusDetailComponent
          ),
      },
      {
        path: 'progress',
        loadComponent: () =>
          import('./features/progress/progress-dashboard.component').then(
            (m) => m.ProgressDashboardComponent
          ),
      },
      {
        path: 'progress/:studentId',
        loadComponent: () =>
          import('./features/progress/student-progress.component').then(
            (m) => m.StudentProgressComponent
          ),
      },
      {
        path: 'exams',
        loadComponent: () =>
          import('./features/exams/exam-list.component').then(
            (m) => m.ExamListComponent
          ),
      },
      {
        path: 'exams/:id',
        loadComponent: () =>
          import('./features/exams/exam-take.component').then(
            (m) => m.ExamTakeComponent
          ),
      },
      {
        path: 'exams/:id/results',
        loadComponent: () =>
          import('./features/exams/exam-results.component').then(
            (m) => m.ExamResultsComponent
          ),
      },
      {
        path: 'certificates',
        loadComponent: () =>
          import('./features/certificates/certificate-list.component').then(
            (m) => m.CertificateListComponent
          ),
      },
      {
        path: 'certificates/:id',
        loadComponent: () =>
          import('./features/certificates/certificate-detail.component').then(
            (m) => m.CertificateDetailComponent
          ),
      },
      {
        path: 'courses',
        loadComponent: () =>
          import('./features/courses/course-list.component').then(
            (m) => m.CourseListComponent
          ),
      },
      {
        path: 'courses/:id',
        loadComponent: () =>
          import('./features/courses/course-player.component').then(
            (m) => m.CoursePlayerComponent
          ),
      },
    ],
  },
];
