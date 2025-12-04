# 📊 MODÜL 13: RAPORLAMA SERVİSİ (Reporting Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | reporting-service |
| Port | 8012 |
| Veritabanı | reporting_db (Read Replica) |
| Cache | Redis |
| Prefix | /api/v1/reports |

### 1.2 Sorumluluklar

- Dashboard ve KPI metrikleri
- Operasyonel raporlar
- Finansal raporlar
- Eğitim ilerleme raporları
- Uçak kullanım raporları
- Düzenleyici uyum raporları
- Rapor şablonları ve zamanlama
- Export (PDF, Excel, CSV)

---

## 2. VERİTABANI ŞEMASI

### 2.1 Report Definitions (Rapor Tanımları)

```sql
-- =============================================================================
-- REPORT_DEFINITIONS (Rapor Tanımları)
-- =============================================================================
CREATE TABLE report_definitions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID,  -- NULL ise sistem raporu
    
    -- Tanımlama
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Kategori
    category                VARCHAR(50) NOT NULL,
    -- operations, finance, training, maintenance, 
    -- compliance, utilization, safety
    
    -- Tip
    report_type             VARCHAR(20) DEFAULT 'standard',
    -- standard, dashboard, scheduled, adhoc
    
    -- Veri Kaynağı
    data_source             VARCHAR(50) NOT NULL,
    -- flights, bookings, students, aircraft, finances, training
    
    -- Query
    base_query              TEXT,  -- SQL veya query builder JSON
    query_type              VARCHAR(20) DEFAULT 'sql',
    -- sql, builder, aggregation
    
    -- Parametreler
    parameters              JSONB DEFAULT '[]',
    -- [
    --   {"name": "start_date", "type": "date", "required": true},
    --   {"name": "aircraft_id", "type": "uuid", "required": false}
    -- ]
    
    -- Kolonlar
    columns                 JSONB DEFAULT '[]',
    -- [
    --   {"field": "flight_date", "label": "Date", "type": "date", "format": "YYYY-MM-DD"},
    --   {"field": "total_hours", "label": "Hours", "type": "decimal", "aggregate": "sum"}
    -- ]
    
    -- Gruplama ve Sıralama
    default_grouping        JSONB,
    default_sorting         JSONB,
    
    -- Görselleştirme
    chart_config            JSONB,
    -- {"type": "bar", "x_axis": "month", "y_axis": "hours"}
    
    -- Export
    export_formats          TEXT[] DEFAULT '{pdf,xlsx,csv}',
    export_template         TEXT,
    
    -- Erişim
    access_roles            TEXT[],  -- Boş ise herkese açık
    is_public               BOOLEAN DEFAULT false,
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    is_system               BOOLEAN DEFAULT false,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_reports_org ON report_definitions(organization_id);
CREATE INDEX idx_reports_category ON report_definitions(category);
```

### 2.2 Scheduled Reports (Zamanlanmış Raporlar)

```sql
-- =============================================================================
-- SCHEDULED_REPORTS (Zamanlanmış Raporlar)
-- =============================================================================
CREATE TABLE scheduled_reports (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    report_definition_id    UUID NOT NULL REFERENCES report_definitions(id),
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    
    -- Zamanlama
    schedule_type           VARCHAR(20) NOT NULL,
    -- daily, weekly, monthly, quarterly, yearly
    
    schedule_config         JSONB NOT NULL,
    -- daily: {"time": "08:00"}
    -- weekly: {"day": 1, "time": "08:00"}  -- 1=Monday
    -- monthly: {"day": 1, "time": "08:00"}
    
    timezone                VARCHAR(50) DEFAULT 'UTC',
    
    -- Parametreler
    report_parameters       JSONB DEFAULT '{}',
    
    -- Alıcılar
    recipients              JSONB DEFAULT '[]',
    -- [{"type": "email", "value": "user@example.com"}, {"type": "user_id", "value": "uuid"}]
    
    -- Export
    export_format           VARCHAR(20) DEFAULT 'pdf',
    
    -- Son Çalıştırma
    last_run_at             TIMESTAMP,
    last_run_status         VARCHAR(20),
    last_run_error          TEXT,
    next_run_at             TIMESTAMP,
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_scheduled_next_run ON scheduled_reports(next_run_at) 
    WHERE is_active = true;
```

### 2.3 Report Executions (Rapor Çalıştırmaları)

```sql
-- =============================================================================
-- REPORT_EXECUTIONS (Rapor Çalıştırma Geçmişi)
-- =============================================================================
CREATE TABLE report_executions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    report_definition_id    UUID NOT NULL REFERENCES report_definitions(id),
    scheduled_report_id     UUID REFERENCES scheduled_reports(id),
    
    -- Parametreler
    parameters              JSONB,
    
    -- Çalıştırma
    started_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at            TIMESTAMP,
    duration_ms             INTEGER,
    
    -- Sonuç
    status                  VARCHAR(20) DEFAULT 'running',
    -- running, completed, failed, cancelled
    
    row_count               INTEGER,
    error_message           TEXT,
    
    -- Çıktı
    result_file_path        VARCHAR(500),
    result_file_size        BIGINT,
    result_format           VARCHAR(20),
    
    -- Cache
    cache_key               VARCHAR(255),
    cache_expires_at        TIMESTAMP,
    
    -- Kullanıcı
    executed_by             UUID,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_executions_report ON report_executions(report_definition_id);
CREATE INDEX idx_executions_org ON report_executions(organization_id, created_at);
```

### 2.4 Dashboard Widgets (Dashboard Bileşenleri)

```sql
-- =============================================================================
-- DASHBOARD_WIDGETS (Dashboard Bileşenleri)
-- =============================================================================
CREATE TABLE dashboard_widgets (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID,
    
    -- Tanımlama
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Tip
    widget_type             VARCHAR(50) NOT NULL,
    -- metric, chart, table, list, map, calendar
    
    -- Veri
    data_source             VARCHAR(50) NOT NULL,
    query_config            JSONB NOT NULL,
    
    -- Görselleştirme
    chart_type              VARCHAR(50),
    -- bar, line, pie, donut, area, scatter
    
    display_config          JSONB DEFAULT '{}',
    -- {"color": "#3B82F6", "icon": "plane", "format": "number"}
    
    -- Boyut
    default_width           INTEGER DEFAULT 1,  -- Grid units
    default_height          INTEGER DEFAULT 1,
    min_width               INTEGER DEFAULT 1,
    min_height              INTEGER DEFAULT 1,
    
    -- Yenileme
    refresh_interval        INTEGER DEFAULT 300,  -- saniye
    
    -- Erişim
    access_roles            TEXT[],
    
    is_active               BOOLEAN DEFAULT true,
    is_system               BOOLEAN DEFAULT false,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- USER_DASHBOARDS (Kullanıcı Dashboard'ları)
-- =============================================================================
CREATE TABLE user_dashboards (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    is_default              BOOLEAN DEFAULT false,
    
    -- Layout
    layout                  JSONB NOT NULL,
    -- [
    --   {"widget_id": "uuid", "x": 0, "y": 0, "w": 2, "h": 1, "config": {}},
    --   ...
    -- ]
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_dashboards ON user_dashboards(user_id);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/reporting.py

import uuid
from django.db import models
from common.models import TenantModel


class ReportDefinition(models.Model):
    """Rapor tanımı modeli"""
    
    class Category(models.TextChoices):
        OPERATIONS = 'operations', 'Operasyonlar'
        FINANCE = 'finance', 'Finans'
        TRAINING = 'training', 'Eğitim'
        MAINTENANCE = 'maintenance', 'Bakım'
        COMPLIANCE = 'compliance', 'Uyum'
        UTILIZATION = 'utilization', 'Kullanım'
        SAFETY = 'safety', 'Güvenlik'
    
    class ReportType(models.TextChoices):
        STANDARD = 'standard', 'Standart'
        DASHBOARD = 'dashboard', 'Dashboard'
        SCHEDULED = 'scheduled', 'Zamanlanmış'
        ADHOC = 'adhoc', 'Anlık'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(blank=True, null=True)
    
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    category = models.CharField(max_length=50, choices=Category.choices)
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.STANDARD
    )
    
    data_source = models.CharField(max_length=50)
    base_query = models.TextField(blank=True, null=True)
    query_type = models.CharField(max_length=20, default='sql')
    
    parameters = models.JSONField(default=list)
    columns = models.JSONField(default=list)
    
    default_grouping = models.JSONField(blank=True, null=True)
    default_sorting = models.JSONField(blank=True, null=True)
    
    chart_config = models.JSONField(blank=True, null=True)
    
    export_formats = models.JSONField(default=lambda: ['pdf', 'xlsx', 'csv'])
    
    access_roles = models.JSONField(default=list)
    is_public = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_definitions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class ScheduledReport(TenantModel):
    """Zamanlanmış rapor modeli"""
    
    class ScheduleType(models.TextChoices):
        DAILY = 'daily', 'Günlük'
        WEEKLY = 'weekly', 'Haftalık'
        MONTHLY = 'monthly', 'Aylık'
        QUARTERLY = 'quarterly', '3 Aylık'
        YEARLY = 'yearly', 'Yıllık'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    report_definition = models.ForeignKey(
        ReportDefinition,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    
    name = models.CharField(max_length=255)
    
    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices
    )
    schedule_config = models.JSONField()
    timezone = models.CharField(max_length=50, default='UTC')
    
    report_parameters = models.JSONField(default=dict)
    recipients = models.JSONField(default=list)
    
    export_format = models.CharField(max_length=20, default='pdf')
    
    last_run_at = models.DateTimeField(blank=True, null=True)
    last_run_status = models.CharField(max_length=20, blank=True, null=True)
    next_run_at = models.DateTimeField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)
    
    class Meta:
        db_table = 'scheduled_reports'
    
    def __str__(self):
        return self.name


class DashboardWidget(models.Model):
    """Dashboard widget modeli"""
    
    class WidgetType(models.TextChoices):
        METRIC = 'metric', 'Metrik'
        CHART = 'chart', 'Grafik'
        TABLE = 'table', 'Tablo'
        LIST = 'list', 'Liste'
        MAP = 'map', 'Harita'
        CALENDAR = 'calendar', 'Takvim'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(blank=True, null=True)
    
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    widget_type = models.CharField(max_length=50, choices=WidgetType.choices)
    
    data_source = models.CharField(max_length=50)
    query_config = models.JSONField()
    
    chart_type = models.CharField(max_length=50, blank=True, null=True)
    display_config = models.JSONField(default=dict)
    
    default_width = models.IntegerField(default=1)
    default_height = models.IntegerField(default=1)
    
    refresh_interval = models.IntegerField(default=300)
    
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dashboard_widgets'
    
    def __str__(self):
        return self.name
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# REPORTING API
# =============================================================================

# Dashboard
GET /api/v1/reports/dashboard:
  summary: Dashboard verileri

GET /api/v1/reports/dashboard/widgets:
  summary: Kullanılabilir widget'lar

GET /api/v1/reports/dashboard/widget/{id}/data:
  summary: Widget verisi

PUT /api/v1/reports/dashboard/layout:
  summary: Dashboard layout kaydet

# KPIs
GET /api/v1/reports/kpis:
  summary: Temel KPI metrikleri
  parameters:
    - name: period
      enum: [today, week, month, quarter, year]

GET /api/v1/reports/kpis/trends:
  summary: KPI trendleri

# Reports
GET /api/v1/reports:
  summary: Rapor listesi
  parameters:
    - name: category

GET /api/v1/reports/{id}:
  summary: Rapor tanımı

POST /api/v1/reports/{id}/execute:
  summary: Raporu çalıştır
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            parameters:
              type: object
            format:
              type: string
              enum: [json, pdf, xlsx, csv]

GET /api/v1/reports/{id}/preview:
  summary: Rapor önizleme (ilk N satır)

GET /api/v1/reports/executions/{id}:
  summary: Çalıştırma sonucu

GET /api/v1/reports/executions/{id}/download:
  summary: Sonucu indir

# Scheduled Reports
GET /api/v1/reports/scheduled:
  summary: Zamanlanmış raporlar

POST /api/v1/reports/scheduled:
  summary: Zamanlanmış rapor oluştur

PUT /api/v1/reports/scheduled/{id}:
  summary: Zamanlanmış rapor güncelle

DELETE /api/v1/reports/scheduled/{id}:
  summary: Zamanlanmış rapor sil

# Pre-built Reports
GET /api/v1/reports/operations/flight-summary:
  summary: Uçuş özeti raporu

GET /api/v1/reports/operations/aircraft-utilization:
  summary: Uçak kullanım raporu

GET /api/v1/reports/training/student-progress:
  summary: Öğrenci ilerleme raporu

GET /api/v1/reports/finance/revenue:
  summary: Gelir raporu

GET /api/v1/reports/finance/aging:
  summary: Alacak yaşlandırma raporu

GET /api/v1/reports/compliance/certificate-expiry:
  summary: Sertifika vade raporu

GET /api/v1/reports/maintenance/upcoming:
  summary: Yaklaşan bakımlar raporu
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/reporting_service.py

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
from django.db import connection
from django.core.cache import cache

from apps.core.models import ReportDefinition, ReportExecution, DashboardWidget
from common.events import EventBus


class ReportingService:
    def __init__(self):
        self.event_bus = EventBus()
    
    async def get_dashboard_kpis(
        self,
        organization_id: str,
        period: str = 'month'
    ) -> Dict[str, Any]:
        """Dashboard KPI'larını getir"""
        
        cache_key = f"kpis:{organization_id}:{period}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Tarih aralığı
        today = date.today()
        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        else:  # year
            start_date = today - timedelta(days=365)
        
        kpis = {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': today.isoformat(),
            'metrics': {}
        }
        
        # Flight metrics
        flight_stats = await self._get_flight_stats(organization_id, start_date)
        kpis['metrics']['flights'] = flight_stats
        
        # Revenue metrics
        revenue_stats = await self._get_revenue_stats(organization_id, start_date)
        kpis['metrics']['revenue'] = revenue_stats
        
        # Utilization
        utilization = await self._get_utilization_stats(organization_id, start_date)
        kpis['metrics']['utilization'] = utilization
        
        # Training
        training_stats = await self._get_training_stats(organization_id, start_date)
        kpis['metrics']['training'] = training_stats
        
        # Cache 5 dakika
        cache.set(cache_key, kpis, 300)
        
        return kpis
    
    async def execute_report(
        self,
        report_id: str,
        organization_id: str,
        user_id: str,
        parameters: Dict[str, Any] = None,
        format: str = 'json',
        limit: int = None
    ) -> Dict[str, Any]:
        """Raporu çalıştır"""
        
        report = await ReportDefinition.objects.aget(id=report_id)
        
        # Execution kaydı oluştur
        execution = await ReportExecution.objects.acreate(
            organization_id=organization_id,
            report_definition=report,
            parameters=parameters or {},
            executed_by=user_id
        )
        
        try:
            # Query'yi hazırla
            query = self._build_query(report, parameters or {}, organization_id)
            
            # Çalıştır
            results = await self._execute_query(query, limit)
            
            # Format
            if format == 'json':
                output = results
            elif format == 'pdf':
                output = await self._generate_pdf_report(report, results)
            elif format == 'xlsx':
                output = await self._generate_excel_report(report, results)
            elif format == 'csv':
                output = await self._generate_csv_report(report, results)
            
            # Execution güncelle
            execution.status = 'completed'
            execution.completed_at = datetime.now()
            execution.row_count = len(results) if isinstance(results, list) else 0
            execution.result_format = format
            await execution.asave()
            
            return {
                'execution_id': str(execution.id),
                'status': 'completed',
                'row_count': execution.row_count,
                'data': output if format == 'json' else None,
                'download_url': output if format != 'json' else None
            }
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            await execution.asave()
            raise
    
    async def get_widget_data(
        self,
        widget_id: str,
        organization_id: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Widget verisini getir"""
        
        widget = await DashboardWidget.objects.aget(id=widget_id)
        
        # Cache kontrolü
        cache_key = f"widget:{widget_id}:{organization_id}:{json.dumps(parameters or {}, sort_keys=True)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Veri çek
        data = await self._execute_widget_query(widget, organization_id, parameters)
        
        result = {
            'widget_id': str(widget.id),
            'widget_type': widget.widget_type,
            'chart_type': widget.chart_type,
            'data': data,
            'display_config': widget.display_config
        }
        
        # Cache
        cache.set(cache_key, result, widget.refresh_interval)
        
        return result
    
    # =========================================================================
    # Pre-built Reports
    # =========================================================================
    
    async def get_flight_summary_report(
        self,
        organization_id: str,
        start_date: date,
        end_date: date,
        aircraft_id: str = None,
        pilot_id: str = None
    ) -> Dict[str, Any]:
        """Uçuş özeti raporu"""
        
        query = """
            SELECT 
                f.flight_date,
                COUNT(*) as flight_count,
                SUM(f.flight_time) as total_flight_time,
                SUM(f.landings_day + f.landings_night) as total_landings,
                SUM(f.fuel_used_liters) as total_fuel,
                SUM(f.total_charge) as total_revenue
            FROM flights f
            WHERE f.organization_id = %s
                AND f.flight_date BETWEEN %s AND %s
                AND f.flight_status = 'approved'
        """
        params = [organization_id, start_date, end_date]
        
        if aircraft_id:
            query += " AND f.aircraft_id = %s"
            params.append(aircraft_id)
        
        if pilot_id:
            query += " AND (f.pic_id = %s OR f.student_id = %s)"
            params.extend([pilot_id, pilot_id])
        
        query += " GROUP BY f.flight_date ORDER BY f.flight_date"
        
        results = await self._execute_query(query, params=params)
        
        # Özet hesapla
        summary = {
            'total_flights': sum(r['flight_count'] for r in results),
            'total_hours': sum(float(r['total_flight_time'] or 0) for r in results),
            'total_landings': sum(r['total_landings'] or 0 for r in results),
            'total_fuel': sum(float(r['total_fuel'] or 0) for r in results),
            'total_revenue': sum(float(r['total_revenue'] or 0) for r in results)
        }
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': summary,
            'daily_data': results
        }
    
    async def get_aircraft_utilization_report(
        self,
        organization_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Uçak kullanım raporu"""
        
        query = """
            SELECT 
                a.id as aircraft_id,
                a.registration,
                a.model,
                COUNT(f.id) as flight_count,
                COALESCE(SUM(f.hobbs_time), 0) as total_hobbs,
                COALESCE(SUM(f.flight_time), 0) as total_flight_time,
                COALESCE(SUM(f.total_charge), 0) as total_revenue
            FROM aircraft a
            LEFT JOIN flights f ON f.aircraft_id = a.id 
                AND f.flight_date BETWEEN %s AND %s
                AND f.flight_status = 'approved'
            WHERE a.organization_id = %s
                AND a.status = 'active'
            GROUP BY a.id, a.registration, a.model
            ORDER BY total_hobbs DESC
        """
        
        results = await self._execute_query(
            query, 
            params=[start_date, end_date, organization_id]
        )
        
        # Günlük ortalama hesapla
        days = (end_date - start_date).days + 1
        for r in results:
            r['daily_average_hours'] = round(float(r['total_hobbs'] or 0) / days, 2)
            r['utilization_percent'] = round(
                (float(r['total_hobbs'] or 0) / (days * 8)) * 100, 1  # 8 saat/gün varsayım
            )
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'aircraft': results
        }
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    async def _get_flight_stats(
        self,
        organization_id: str,
        start_date: date
    ) -> Dict[str, Any]:
        """Uçuş istatistiklerini getir"""
        
        query = """
            SELECT 
                COUNT(*) as total_flights,
                COALESCE(SUM(flight_time), 0) as total_hours,
                COALESCE(SUM(landings_day + landings_night), 0) as total_landings
            FROM flights
            WHERE organization_id = %s
                AND flight_date >= %s
                AND flight_status = 'approved'
        """
        
        result = await self._execute_query(query, params=[organization_id, start_date])
        
        return {
            'total_flights': result[0]['total_flights'] if result else 0,
            'total_hours': float(result[0]['total_hours']) if result else 0,
            'total_landings': result[0]['total_landings'] if result else 0
        }
    
    async def _get_revenue_stats(
        self,
        organization_id: str,
        start_date: date
    ) -> Dict[str, Any]:
        """Gelir istatistiklerini getir"""
        
        query = """
            SELECT 
                COALESCE(SUM(amount), 0) as total_revenue
            FROM transactions
            WHERE organization_id = %s
                AND created_at >= %s
                AND transaction_type = 'charge'
                AND status = 'completed'
        """
        
        result = await self._execute_query(query, params=[organization_id, start_date])
        
        return {
            'total_revenue': float(result[0]['total_revenue']) if result else 0
        }
    
    def _build_query(
        self,
        report: ReportDefinition,
        parameters: Dict[str, Any],
        organization_id: str
    ) -> str:
        """Query oluştur"""
        
        query = report.base_query
        
        # Organization filter ekle
        if '{organization_id}' in query:
            query = query.replace('{organization_id}', f"'{organization_id}'")
        
        # Parametreleri uygula
        for param in report.parameters:
            placeholder = '{' + param['name'] + '}'
            if placeholder in query:
                value = parameters.get(param['name'])
                if value is not None:
                    if param['type'] == 'date':
                        query = query.replace(placeholder, f"'{value}'")
                    elif param['type'] == 'string':
                        query = query.replace(placeholder, f"'{value}'")
                    else:
                        query = query.replace(placeholder, str(value))
        
        return query
    
    async def _execute_query(
        self,
        query: str,
        limit: int = None,
        params: list = None
    ) -> List[Dict[str, Any]]:
        """Query çalıştır"""
        
        if limit:
            query += f" LIMIT {limit}"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return results
```

---

## 6. EVENTS

```python
# Reporting Service Events

REPORT_EXECUTED = 'reporting.report_executed'
REPORT_EXPORTED = 'reporting.report_exported'
SCHEDULED_REPORT_RUN = 'reporting.scheduled_run'
SCHEDULED_REPORT_FAILED = 'reporting.scheduled_failed'

# Consumed Events
# Tüm diğer servislerden gelen event'ları dinleyerek
# istatistikleri güncel tutar
```

---

Bu doküman Reporting Service'in tüm detaylarını içermektedir.