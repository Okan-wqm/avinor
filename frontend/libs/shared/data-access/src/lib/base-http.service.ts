import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface QueryParams {
  [key: string]: string | number | boolean | undefined;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Base HTTP service with common CRUD operations
 */
export abstract class BaseHttpService<T> {
  protected abstract endpoint: string;

  constructor(protected http: HttpClient) {}

  /**
   * Get paginated list
   */
  getList(params?: QueryParams): Observable<PaginatedResponse<T>> {
    const httpParams = this.buildParams(params);
    return this.http.get<PaginatedResponse<T>>(this.endpoint, { params: httpParams });
  }

  /**
   * Get single item by ID
   */
  getById(id: string): Observable<T> {
    return this.http.get<T>(`${this.endpoint}${id}/`);
  }

  /**
   * Create new item
   */
  create(data: Partial<T>): Observable<T> {
    return this.http.post<T>(this.endpoint, data);
  }

  /**
   * Update existing item
   */
  update(id: string, data: Partial<T>): Observable<T> {
    return this.http.patch<T>(`${this.endpoint}${id}/`, data);
  }

  /**
   * Replace existing item
   */
  replace(id: string, data: T): Observable<T> {
    return this.http.put<T>(`${this.endpoint}${id}/`, data);
  }

  /**
   * Delete item
   */
  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.endpoint}${id}/`);
  }

  /**
   * Build HttpParams from query params object
   */
  protected buildParams(params?: QueryParams): HttpParams {
    let httpParams = new HttpParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          httpParams = httpParams.set(key, String(value));
        }
      });
    }
    return httpParams;
  }
}
