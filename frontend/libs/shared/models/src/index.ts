// Shared Models - Type Definitions

// User Types
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  status: UserStatus;
  organization_id?: string;
  created_at: string;
  last_login?: string;
}

export type UserRole = 'student' | 'instructor' | 'staff' | 'admin';
export type UserStatus = 'active' | 'inactive' | 'suspended';

// Aircraft Types
export interface Aircraft {
  id: string;
  registration: string;
  type: string;
  model: string;
  year: number;
  status: AircraftStatus;
  total_hours: number;
  hours_to_next_service: number;
  hourly_rate: number;
  organization_id: string;
}

export type AircraftStatus = 'available' | 'in_flight' | 'maintenance' | 'grounded';

// Booking Types
export interface Booking {
  id: string;
  aircraft_id: string;
  user_id: string;
  instructor_id?: string;
  start_time: string;
  end_time: string;
  status: BookingStatus;
  booking_type: BookingType;
  notes?: string;
  created_at: string;
}

export type BookingStatus = 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled';
export type BookingType = 'solo' | 'dual' | 'check_ride' | 'maintenance';

// Flight Types
export interface Flight {
  id: string;
  booking_id?: string;
  aircraft_id: string;
  pic_id: string;
  sic_id?: string;
  departure_airport: string;
  arrival_airport: string;
  departure_time: string;
  arrival_time?: string;
  hobbs_start: number;
  hobbs_end?: number;
  tach_start: number;
  tach_end?: number;
  status: FlightStatus;
}

export type FlightStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

// Training Types
export interface Syllabus {
  id: string;
  name: string;
  description: string;
  license_type: LicenseType;
  total_lessons: number;
  total_flight_hours: number;
  total_ground_hours: number;
  status: 'draft' | 'active' | 'archived';
}

export type LicenseType = 'PPL' | 'CPL' | 'ATPL' | 'IR' | 'MEP';

export interface TrainingProgress {
  id: string;
  student_id: string;
  syllabus_id: string;
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  flight_hours_logged: number;
  status: 'active' | 'paused' | 'completed';
}

// Certificate Types
export interface Certificate {
  id: string;
  holder_id: string;
  type: CertificateType;
  name: string;
  number: string;
  issue_date: string;
  expiry_date?: string;
  issuing_authority: string;
  status: CertificateStatus;
}

export type CertificateType = 'license' | 'rating' | 'endorsement' | 'medical';
export type CertificateStatus = 'valid' | 'expired' | 'suspended' | 'revoked';

// Organization Types
export interface Organization {
  id: string;
  name: string;
  code: string;
  type: OrganizationType;
  status: 'active' | 'inactive';
  created_at: string;
}

export type OrganizationType = 'flight_school' | 'aero_club' | 'commercial';

// Finance Types
export interface Invoice {
  id: string;
  number: string;
  customer_id: string;
  amount: number;
  currency: string;
  status: InvoiceStatus;
  issue_date: string;
  due_date: string;
  paid_date?: string;
}

export type InvoiceStatus = 'draft' | 'pending' | 'paid' | 'overdue' | 'cancelled';

// API Response Types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail: string;
  code?: string;
  field_errors?: Record<string, string[]>;
}

// Weather Types (METAR/TAF)
export interface Weather {
  station: string;
  observation_time: string;
  temperature: number;
  dewpoint: number;
  wind_direction: number;
  wind_speed: number;
  wind_gust?: number;
  visibility: number;
  ceiling?: number;
  flight_category: FlightCategory;
  raw_text: string;
}

export type FlightCategory = 'VFR' | 'MVFR' | 'IFR' | 'LIFR';
