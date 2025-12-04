import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BaseHttpService, PaginatedResponse, QueryParams } from './base-http.service';

// User Service
@Injectable({ providedIn: 'root' })
export class UserApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/users/';
  constructor() { super(inject(HttpClient)); }
}

// Aircraft Service
@Injectable({ providedIn: 'root' })
export class AircraftApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/aircraft/';
  constructor() { super(inject(HttpClient)); }

  getAvailability(id: string, date: string): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(`${this.endpoint}${id}/availability/`, {
      params: { date },
    });
  }
}

// Booking Service
@Injectable({ providedIn: 'root' })
export class BookingApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/bookings/';
  constructor() { super(inject(HttpClient)); }

  confirm(id: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}${id}/confirm/`, {});
  }

  cancel(id: string, reason?: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}${id}/cancel/`, { reason });
  }

  checkIn(id: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}${id}/check-in/`, {});
  }
}

// Flight Service
@Injectable({ providedIn: 'root' })
export class FlightApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/flights/';
  constructor() { super(inject(HttpClient)); }

  start(id: string, data: { hobbs_start: number; tach_start: number }): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}${id}/start/`, data);
  }

  complete(id: string, data: { hobbs_end: number; tach_end: number; notes?: string }): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}${id}/complete/`, data);
  }
}

// Training Service
@Injectable({ providedIn: 'root' })
export class TrainingApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/training/';
  constructor() { super(inject(HttpClient)); }

  getSyllabi(params?: QueryParams): Observable<PaginatedResponse<Record<string, unknown>>> {
    return this.http.get<PaginatedResponse<Record<string, unknown>>>(`${this.endpoint}syllabi/`, {
      params: this.buildParams(params),
    });
  }

  getProgress(studentId: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.endpoint}progress/${studentId}/`);
  }
}

// Theory/Exam Service
@Injectable({ providedIn: 'root' })
export class TheoryApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/theory/';
  constructor() { super(inject(HttpClient)); }

  getExams(params?: QueryParams): Observable<PaginatedResponse<Record<string, unknown>>> {
    return this.http.get<PaginatedResponse<Record<string, unknown>>>(`${this.endpoint}exams/`, {
      params: this.buildParams(params),
    });
  }

  startExam(examId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}exams/${examId}/start/`, {});
  }

  submitExam(examId: string, answers: { question_id: string; answer_id: string }[]): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}exams/${examId}/submit/`, { answers });
  }

  getCourses(params?: QueryParams): Observable<PaginatedResponse<Record<string, unknown>>> {
    return this.http.get<PaginatedResponse<Record<string, unknown>>>(`${this.endpoint}courses/`, {
      params: this.buildParams(params),
    });
  }
}

// Certificate Service
@Injectable({ providedIn: 'root' })
export class CertificateApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/certificates/';
  constructor() { super(inject(HttpClient)); }

  verify(id: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}${id}/verify/`, {});
  }
}

// Organization Service
@Injectable({ providedIn: 'root' })
export class OrganizationApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/organizations/';
  constructor() { super(inject(HttpClient)); }
}

// Weather Service
@Injectable({ providedIn: 'root' })
export class WeatherApiService {
  private http = inject(HttpClient);
  private endpoint = '/api/v1/weather/';

  getMetar(station: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.endpoint}metar/${station}/`);
  }

  getTaf(station: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.endpoint}taf/${station}/`);
  }

  getMultipleMetars(stations: string[]): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(`${this.endpoint}metar/`, {
      params: { stations: stations.join(',') },
    });
  }
}

// Finance Service
@Injectable({ providedIn: 'root' })
export class FinanceApiService extends BaseHttpService<Record<string, unknown>> {
  protected endpoint = '/api/v1/finance/';
  constructor() { super(inject(HttpClient)); }

  getInvoices(params?: QueryParams): Observable<PaginatedResponse<Record<string, unknown>>> {
    return this.http.get<PaginatedResponse<Record<string, unknown>>>(`${this.endpoint}invoices/`, {
      params: this.buildParams(params),
    });
  }

  createInvoice(data: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}invoices/`, data);
  }

  recordPayment(invoiceId: string, data: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.endpoint}invoices/${invoiceId}/pay/`, data);
  }
}
