# services/organization-service/src/apps/core/models/safety_management.py
"""
Safety Management System (SMS) Models

Implements EASA Part-ORA.GEN.200 and ICAO Doc 9859 SMS requirements:
- Safety policy and objectives
- Safety risk management
- Safety assurance
- Safety promotion

Reference: ICAO Doc 9859 - Safety Management Manual (4th Edition)
Reference: EASA AMC1 ORA.GEN.200(a)(1) - Management System
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class SafetyPolicy(models.Model):
    """
    Organization's safety policy document.

    Per ICAO Doc 9859 Chapter 5:
    - Management commitment and responsibility
    - Safety accountabilities
    - Appointment of key safety personnel
    - Coordination of emergency response planning
    - SMS documentation
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Policy Information
    version = models.CharField(max_length=20)
    effective_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)

    # Policy Content
    policy_statement = models.TextField(
        help_text="Senior management safety commitment statement"
    )
    safety_objectives = models.JSONField(
        default=list,
        help_text="List of measurable safety objectives"
    )

    # Key Personnel
    accountable_manager_id = models.UUIDField(
        help_text="Person with overall SMS accountability"
    )
    safety_manager_id = models.UUIDField(
        help_text="Designated safety manager"
    )
    safety_committee_members = ArrayField(
        models.UUIDField(),
        default=list,
        help_text="Safety Review Board/Committee members"
    )

    # Policy Commitments
    just_culture_policy = models.TextField(
        blank=True, null=True,
        help_text="Just culture and non-punitive reporting policy"
    )
    resource_commitment = models.TextField(
        blank=True, null=True,
        help_text="Commitment to allocate resources for SMS"
    )

    # Document Management
    document_url = models.URLField(max_length=500, blank=True, null=True)
    approved_by_id = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    is_current = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'safety_policies'
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['organization_id', 'is_current']),
            models.Index(fields=['effective_date']),
        ]

    def __str__(self):
        return f"Safety Policy v{self.version} ({self.effective_date})"


class HazardRegister(models.Model):
    """
    Hazard identification and tracking register.

    Per ICAO Doc 9859 Chapter 6:
    - Reactive hazard identification (from incidents)
    - Proactive hazard identification (audits, assessments)
    - Predictive hazard identification (data analysis)
    """

    class HazardCategory(models.TextChoices):
        TECHNICAL = 'technical', 'Technical/Equipment'
        ENVIRONMENTAL = 'environmental', 'Environmental/Weather'
        HUMAN_FACTORS = 'human_factors', 'Human Factors'
        ORGANIZATIONAL = 'organizational', 'Organizational'
        REGULATORY = 'regulatory', 'Regulatory/Compliance'
        AIRPORT = 'airport', 'Airport/Aerodrome'
        AIRSPACE = 'airspace', 'Airspace/ATC'
        WILDLIFE = 'wildlife', 'Wildlife'
        THIRD_PARTY = 'third_party', 'Third Party/Contractor'
        SECURITY = 'security', 'Security Related'

    class IdentificationMethod(models.TextChoices):
        REACTIVE = 'reactive', 'Reactive (Incident/Occurrence)'
        PROACTIVE = 'proactive', 'Proactive (Audit/Inspection)'
        PREDICTIVE = 'predictive', 'Predictive (Data Analysis)'
        BRAINSTORMING = 'brainstorming', 'Brainstorming Session'
        EXTERNAL = 'external', 'External Source/SIB'
        CHANGE_MANAGEMENT = 'change_management', 'Change Management'

    class Status(models.TextChoices):
        IDENTIFIED = 'identified', 'Identified'
        UNDER_ASSESSMENT = 'under_assessment', 'Under Assessment'
        MITIGATED = 'mitigated', 'Mitigated'
        ACCEPTED = 'accepted', 'Accepted'
        MONITORED = 'monitored', 'Monitored'
        CLOSED = 'closed', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Hazard Identification
    hazard_number = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=HazardCategory.choices)

    identification_method = models.CharField(
        max_length=30,
        choices=IdentificationMethod.choices
    )
    identification_date = models.DateField(default=date.today)
    identified_by_id = models.UUIDField()

    # Source Reference
    source_occurrence_id = models.UUIDField(
        blank=True, null=True,
        help_text="If reactive, linked occurrence report"
    )
    source_audit_id = models.UUIDField(
        blank=True, null=True,
        help_text="If proactive, linked audit finding"
    )

    # Location Context
    affected_operations = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="Operations affected: training, charter, etc."
    )
    affected_aircraft_types = ArrayField(
        models.CharField(max_length=10),
        default=list,
        help_text="Aircraft types affected"
    )
    affected_locations = ArrayField(
        models.CharField(max_length=10),
        default=list,
        help_text="Airports/locations affected (ICAO codes)"
    )

    # Risk Assessment (before mitigation)
    initial_likelihood = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Improbable, 5=Frequent"
    )
    initial_severity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Negligible, 5=Catastrophic"
    )

    # Residual Risk (after mitigation)
    residual_likelihood = models.IntegerField(
        blank=True, null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    residual_severity = models.IntegerField(
        blank=True, null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Status Tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDENTIFIED
    )
    owner_id = models.UUIDField(
        help_text="Person responsible for managing this hazard"
    )
    review_date = models.DateField(blank=True, null=True)
    next_review_date = models.DateField(blank=True, null=True)

    # Closure
    closed_date = models.DateField(blank=True, null=True)
    closure_reason = models.TextField(blank=True, null=True)
    closed_by_id = models.UUIDField(blank=True, null=True)

    # Documentation
    attachments = models.JSONField(default=list)
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hazard_register'
        ordering = ['-identification_date']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['category']),
            models.Index(fields=['next_review_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'hazard_number'],
                name='unique_hazard_number'
            )
        ]

    def __str__(self):
        return f"{self.hazard_number}: {self.title}"

    @property
    def initial_risk_index(self) -> int:
        """Calculate initial risk index (likelihood x severity)."""
        return self.initial_likelihood * self.initial_severity

    @property
    def residual_risk_index(self) -> int:
        """Calculate residual risk index after mitigation."""
        if self.residual_likelihood and self.residual_severity:
            return self.residual_likelihood * self.residual_severity
        return self.initial_risk_index

    @property
    def risk_level(self) -> str:
        """
        Determine risk level based on 5x5 matrix.
        Per ICAO Doc 9859 Figure 5-4.
        """
        index = self.residual_risk_index
        if index >= 15:
            return 'INTOLERABLE'
        elif index >= 10:
            return 'TOLERABLE_WITH_MITIGATION'
        elif index >= 5:
            return 'ACCEPTABLE_WITH_REVIEW'
        else:
            return 'ACCEPTABLE'


class RiskMitigation(models.Model):
    """
    Risk mitigation actions/controls for hazards.

    Per ICAO Doc 9859 Chapter 6 - Safety Risk Mitigation:
    - Elimination
    - Reduction/Substitution
    - Exposure limitation
    - Protective measures
    """

    class MitigationType(models.TextChoices):
        ELIMINATION = 'elimination', 'Elimination'
        SUBSTITUTION = 'substitution', 'Substitution'
        ENGINEERING = 'engineering', 'Engineering Control'
        ADMINISTRATIVE = 'administrative', 'Administrative Control'
        PPE = 'ppe', 'Protective Equipment'
        TRAINING = 'training', 'Training/Awareness'
        PROCEDURE = 'procedure', 'Procedure Change'
        EQUIPMENT = 'equipment', 'Equipment Change'

    class Status(models.TextChoices):
        PROPOSED = 'proposed', 'Proposed'
        APPROVED = 'approved', 'Approved'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IMPLEMENTED = 'implemented', 'Implemented'
        VERIFIED = 'verified', 'Verified Effective'
        REJECTED = 'rejected', 'Rejected'
        DEFERRED = 'deferred', 'Deferred'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    hazard = models.ForeignKey(
        HazardRegister,
        on_delete=models.CASCADE,
        related_name='mitigations'
    )

    # Mitigation Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    mitigation_type = models.CharField(
        max_length=20,
        choices=MitigationType.choices
    )

    # Expected Risk Reduction
    expected_likelihood_reduction = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(4)]
    )
    expected_severity_reduction = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(4)]
    )

    # Implementation
    responsible_person_id = models.UUIDField()
    target_date = models.DateField()
    actual_completion_date = models.DateField(blank=True, null=True)

    # Resources
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    resources_required = models.TextField(blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED
    )

    # Approval
    approved_by_id = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)

    # Verification
    verification_method = models.TextField(
        blank=True, null=True,
        help_text="How effectiveness will be verified"
    )
    verified_by_id = models.UUIDField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)

    # Priority
    priority = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Highest priority"
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'risk_mitigations'
        ordering = ['priority', 'target_date']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['target_date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"


class SafetyOccurrence(models.Model):
    """
    Safety occurrence/incident report.

    Per EASA Regulation (EU) No 376/2014 - Occurrence Reporting:
    - Mandatory Occurrence Reports (MOR)
    - Voluntary Occurrence Reports (VOR)
    - Internal Safety Reports

    Reference: ICAO Annex 13 - Aircraft Accident Investigation
    """

    class OccurrenceType(models.TextChoices):
        ACCIDENT = 'accident', 'Accident'
        SERIOUS_INCIDENT = 'serious_incident', 'Serious Incident'
        INCIDENT = 'incident', 'Incident'
        NEAR_MISS = 'near_miss', 'Near Miss'
        HAZARD_REPORT = 'hazard_report', 'Hazard Report'
        SAFETY_CONCERN = 'safety_concern', 'Safety Concern'
        GROUND_INCIDENT = 'ground_incident', 'Ground Incident'

    class ReportingBasis(models.TextChoices):
        MANDATORY = 'mandatory', 'Mandatory (MOR)'
        VOLUNTARY = 'voluntary', 'Voluntary (VOR)'
        INTERNAL = 'internal', 'Internal Report'
        ANONYMOUS = 'anonymous', 'Anonymous'

    class Phase(models.TextChoices):
        PREFLIGHT = 'preflight', 'Pre-flight'
        TAXI = 'taxi', 'Taxi'
        TAKEOFF = 'takeoff', 'Take-off'
        CLIMB = 'climb', 'Climb'
        CRUISE = 'cruise', 'Cruise'
        DESCENT = 'descent', 'Descent'
        APPROACH = 'approach', 'Approach'
        LANDING = 'landing', 'Landing'
        POST_FLIGHT = 'post_flight', 'Post-flight'
        MAINTENANCE = 'maintenance', 'Maintenance'
        GROUND_OPS = 'ground_ops', 'Ground Operations'
        NOT_APPLICABLE = 'na', 'Not Applicable'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_INVESTIGATION = 'under_investigation', 'Under Investigation'
        PENDING_ACTIONS = 'pending_actions', 'Pending Actions'
        CLOSED = 'closed', 'Closed'
        REOPENED = 'reopened', 'Reopened'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Report Identification
    report_number = models.CharField(max_length=50, db_index=True)
    occurrence_type = models.CharField(
        max_length=20,
        choices=OccurrenceType.choices
    )
    reporting_basis = models.CharField(
        max_length=20,
        choices=ReportingBasis.choices
    )

    # Occurrence Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    occurrence_date = models.DateField()
    occurrence_time = models.TimeField(blank=True, null=True)
    occurrence_time_utc = models.TimeField(blank=True, null=True)

    # Location
    location_description = models.CharField(max_length=255, blank=True, null=True)
    airport_icao = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="ICAO airport code if applicable"
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=7,
        blank=True,
        null=True
    )
    altitude_ft = models.IntegerField(blank=True, null=True)

    # Flight Phase
    flight_phase = models.CharField(
        max_length=20,
        choices=Phase.choices,
        default=Phase.NOT_APPLICABLE
    )

    # Aircraft Information
    aircraft_id = models.UUIDField(blank=True, null=True)
    aircraft_registration = models.CharField(max_length=20, blank=True, null=True)
    aircraft_type = models.CharField(max_length=20, blank=True, null=True)

    # Flight Information
    flight_number = models.CharField(max_length=20, blank=True, null=True)
    departure_airport = models.CharField(max_length=4, blank=True, null=True)
    destination_airport = models.CharField(max_length=4, blank=True, null=True)

    # Personnel Involved
    pic_id = models.UUIDField(blank=True, null=True)
    crew_members = ArrayField(
        models.UUIDField(),
        default=list,
        help_text="Other crew member IDs"
    )
    persons_injured = models.IntegerField(default=0)
    persons_fatal = models.IntegerField(default=0)

    # Weather Conditions
    weather_conditions = models.JSONField(
        default=dict,
        help_text="METAR, visibility, wind, etc."
    )

    # Damage
    aircraft_damage = models.CharField(
        max_length=20,
        choices=[
            ('none', 'None'),
            ('minor', 'Minor'),
            ('substantial', 'Substantial'),
            ('destroyed', 'Destroyed'),
        ],
        default='none'
    )
    other_damage = models.TextField(blank=True, null=True)

    # ECCAIRS Taxonomy (European Coordination Centre for Accident Reporting)
    eccairs_categories = ArrayField(
        models.CharField(max_length=20),
        default=list,
        help_text="ECCAIRS occurrence category codes"
    )

    # Reporter Information
    reporter_id = models.UUIDField(blank=True, null=True)
    reporter_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="For anonymous reports"
    )
    reporter_role = models.CharField(max_length=50, blank=True, null=True)
    reporter_contact = models.CharField(max_length=255, blank=True, null=True)
    is_confidential = models.BooleanField(
        default=False,
        help_text="Reporter identity protected"
    )

    # Status and Processing
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    submitted_at = models.DateTimeField(blank=True, null=True)

    # Investigation
    investigator_id = models.UUIDField(blank=True, null=True)
    investigation_started = models.DateField(blank=True, null=True)
    investigation_completed = models.DateField(blank=True, null=True)

    # Root Cause Analysis
    immediate_causes = models.JSONField(default=list)
    contributing_factors = models.JSONField(default=list)
    root_causes = models.JSONField(default=list)

    # Linked Hazards
    linked_hazards = models.ManyToManyField(
        HazardRegister,
        blank=True,
        related_name='occurrences'
    )

    # Safety Actions
    immediate_actions = models.TextField(
        blank=True, null=True,
        help_text="Actions taken immediately after occurrence"
    )

    # External Reporting
    reported_to_authority = models.BooleanField(default=False)
    authority_report_date = models.DateField(blank=True, null=True)
    authority_reference = models.CharField(max_length=100, blank=True, null=True)
    authority_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="E.g., CAA, NTSB, AAIB"
    )

    # Documentation
    attachments = models.JSONField(
        default=list,
        help_text="Photos, documents, audio recordings"
    )

    # Closure
    closed_date = models.DateField(blank=True, null=True)
    closed_by_id = models.UUIDField(blank=True, null=True)
    closure_notes = models.TextField(blank=True, null=True)
    lessons_learned = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'safety_occurrences'
        ordering = ['-occurrence_date', '-occurrence_time']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['occurrence_type']),
            models.Index(fields=['occurrence_date']),
            models.Index(fields=['aircraft_registration']),
            models.Index(fields=['airport_icao']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'report_number'],
                name='unique_occurrence_report_number'
            )
        ]

    def __str__(self):
        return f"{self.report_number}: {self.title}"

    @property
    def is_mandatory_report(self) -> bool:
        """Check if this requires mandatory external reporting."""
        return (
            self.occurrence_type in [
                self.OccurrenceType.ACCIDENT,
                self.OccurrenceType.SERIOUS_INCIDENT
            ] or
            self.reporting_basis == self.ReportingBasis.MANDATORY
        )


class SafetyAction(models.Model):
    """
    Corrective and preventive actions from occurrences.

    Per ICAO Doc 9859:
    - Immediate corrective actions
    - Long-term corrective actions
    - Preventive actions
    - Systemic improvements
    """

    class ActionType(models.TextChoices):
        IMMEDIATE = 'immediate', 'Immediate Corrective'
        CORRECTIVE = 'corrective', 'Corrective Action'
        PREVENTIVE = 'preventive', 'Preventive Action'
        SYSTEMIC = 'systemic', 'Systemic Improvement'

    class Status(models.TextChoices):
        PROPOSED = 'proposed', 'Proposed'
        APPROVED = 'approved', 'Approved'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        VERIFIED = 'verified', 'Verified Effective'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Source
    occurrence = models.ForeignKey(
        SafetyOccurrence,
        on_delete=models.CASCADE,
        related_name='safety_actions',
        blank=True,
        null=True
    )
    hazard = models.ForeignKey(
        HazardRegister,
        on_delete=models.CASCADE,
        related_name='safety_actions',
        blank=True,
        null=True
    )
    audit_finding_id = models.UUIDField(
        blank=True, null=True,
        help_text="From internal/external audit"
    )

    # Action Details
    action_number = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices
    )

    # Expected Outcome
    expected_outcome = models.TextField(
        help_text="What will this action achieve?"
    )
    success_criteria = models.TextField(
        blank=True, null=True,
        help_text="How will success be measured?"
    )

    # Responsibility
    responsible_person_id = models.UUIDField()
    responsible_department = models.CharField(max_length=100, blank=True, null=True)

    # Timeline
    target_date = models.DateField()
    actual_completion_date = models.DateField(blank=True, null=True)
    extension_count = models.IntegerField(default=0)
    extension_reasons = models.JSONField(default=list)

    # Priority
    priority = models.CharField(
        max_length=10,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED
    )

    # Progress
    progress_notes = models.JSONField(
        default=list,
        help_text="Progress update entries"
    )
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Approval
    approved_by_id = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    # Verification
    verification_required = models.BooleanField(default=True)
    verification_method = models.TextField(blank=True, null=True)
    verified_by_id = models.UUIDField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    verification_evidence = models.JSONField(
        default=list,
        help_text="Documents proving effectiveness"
    )

    # Related Documents
    related_documents = models.JSONField(default=list)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'safety_actions'
        ordering = ['priority', 'target_date']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['target_date']),
            models.Index(fields=['responsible_person_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'action_number'],
                name='unique_action_number'
            )
        ]

    def __str__(self):
        return f"{self.action_number}: {self.title}"

    @property
    def is_overdue(self) -> bool:
        """Check if action is overdue."""
        if self.status in [self.Status.COMPLETED, self.Status.VERIFIED, self.Status.CANCELLED]:
            return False
        return date.today() > self.target_date


class SafetyMeeting(models.Model):
    """
    Safety Review Board / Safety Committee meetings.

    Per ICAO Doc 9859 Chapter 9:
    - Safety performance monitoring
    - Safety data analysis
    - Safety action tracking
    """

    class MeetingType(models.TextChoices):
        SRB = 'srb', 'Safety Review Board'
        SAFETY_COMMITTEE = 'safety_committee', 'Safety Committee'
        MONTHLY_REVIEW = 'monthly_review', 'Monthly Safety Review'
        EMERGENCY = 'emergency', 'Emergency Meeting'
        INVESTIGATION = 'investigation', 'Investigation Review'
        MANAGEMENT_REVIEW = 'management_review', 'Management Review'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Meeting Details
    meeting_type = models.CharField(
        max_length=30,
        choices=MeetingType.choices
    )
    title = models.CharField(max_length=255)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    location = models.CharField(max_length=255, blank=True, null=True)
    virtual_meeting_url = models.URLField(max_length=500, blank=True, null=True)

    # Attendance
    chairperson_id = models.UUIDField()
    attendees = ArrayField(
        models.UUIDField(),
        default=list
    )
    actual_attendees = ArrayField(
        models.UUIDField(),
        default=list,
        help_text="Who actually attended"
    )
    apologies = ArrayField(
        models.UUIDField(),
        default=list
    )

    # Agenda
    agenda = models.JSONField(
        default=list,
        help_text="List of agenda items"
    )

    # Occurrences Reviewed
    occurrences_reviewed = models.ManyToManyField(
        SafetyOccurrence,
        blank=True,
        related_name='reviewed_in_meetings'
    )

    # Hazards Reviewed
    hazards_reviewed = models.ManyToManyField(
        HazardRegister,
        blank=True,
        related_name='reviewed_in_meetings'
    )

    # Actions Reviewed
    actions_reviewed = models.ManyToManyField(
        SafetyAction,
        blank=True,
        related_name='reviewed_in_meetings'
    )

    # Minutes
    minutes = models.TextField(blank=True, null=True)
    minutes_document_url = models.URLField(max_length=500, blank=True, null=True)

    # Decisions
    decisions = models.JSONField(
        default=list,
        help_text="Key decisions made"
    )

    # Safety Metrics Presented
    safety_metrics = models.JSONField(
        default=dict,
        help_text="Safety KPIs discussed"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='scheduled'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'safety_meetings'
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['organization_id', 'scheduled_date']),
            models.Index(fields=['meeting_type']),
        ]

    def __str__(self):
        return f"{self.meeting_type}: {self.title} ({self.scheduled_date})"


class SafetyPerformanceIndicator(models.Model):
    """
    Safety Performance Indicators (SPIs) and Targets.

    Per ICAO Doc 9859 Chapter 7:
    - Accident rates
    - Incident rates
    - Safety action completion rates
    - Compliance rates
    """

    class Category(models.TextChoices):
        LAGGING = 'lagging', 'Lagging Indicator'
        LEADING = 'leading', 'Leading Indicator'

    class Frequency(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUAL = 'annual', 'Annual'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Indicator Definition
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=10,
        choices=Category.choices
    )

    # Measurement
    unit = models.CharField(
        max_length=50,
        help_text="E.g., per 1000 flight hours"
    )
    calculation_method = models.TextField(
        help_text="How the indicator is calculated"
    )
    data_source = models.CharField(
        max_length=255,
        help_text="Where data comes from"
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MONTHLY
    )

    # Targets
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True
    )
    alert_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Trigger alert if exceeded"
    )
    trigger_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Trigger investigation if exceeded"
    )

    # Direction
    lower_is_better = models.BooleanField(
        default=True,
        help_text="True if lower values are safer"
    )

    # Status
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=date.today)
    effective_to = models.DateField(blank=True, null=True)

    # Ownership
    owner_id = models.UUIDField()

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'safety_performance_indicators'
        ordering = ['code']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_spi_code'
            )
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"


class SafetyPerformanceMeasurement(models.Model):
    """
    Actual measurements of safety performance indicators.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    indicator = models.ForeignKey(
        SafetyPerformanceIndicator,
        on_delete=models.CASCADE,
        related_name='measurements'
    )

    # Measurement Period
    period_start = models.DateField()
    period_end = models.DateField()

    # Values
    value = models.DecimalField(max_digits=15, decimal_places=4)
    numerator = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Raw numerator if rate"
    )
    denominator = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Raw denominator if rate"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'Normal'),
            ('alert', 'Alert Level'),
            ('trigger', 'Trigger Level'),
        ],
        default='normal'
    )

    # Analysis
    trend = models.CharField(
        max_length=20,
        choices=[
            ('improving', 'Improving'),
            ('stable', 'Stable'),
            ('declining', 'Declining'),
        ],
        blank=True,
        null=True
    )
    analysis_notes = models.TextField(blank=True, null=True)

    # Verification
    verified = models.BooleanField(default=False)
    verified_by_id = models.UUIDField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recorded_by_id = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'safety_performance_measurements'
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['organization_id', 'period_start']),
            models.Index(fields=['indicator', 'period_start']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['indicator', 'period_start', 'period_end'],
                name='unique_measurement_period'
            )
        ]

    def __str__(self):
        return f"{self.indicator.code}: {self.value} ({self.period_start})"


class SafetyPromotion(models.Model):
    """
    Safety promotion activities.

    Per ICAO Doc 9859 Chapter 8:
    - Training and education
    - Safety communication
    - Safety awareness programs
    """

    class ActivityType(models.TextChoices):
        TRAINING = 'training', 'Safety Training'
        BULLETIN = 'bulletin', 'Safety Bulletin'
        NEWSLETTER = 'newsletter', 'Newsletter'
        POSTER = 'poster', 'Safety Poster'
        VIDEO = 'video', 'Safety Video'
        BRIEFING = 'briefing', 'Safety Briefing'
        CAMPAIGN = 'campaign', 'Safety Campaign'
        WORKSHOP = 'workshop', 'Workshop'
        LESSON_LEARNED = 'lesson_learned', 'Lessons Learned'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Activity Details
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices
    )
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Content
    content = models.TextField(blank=True, null=True)
    content_url = models.URLField(max_length=500, blank=True, null=True)
    attachments = models.JSONField(default=list)

    # Target Audience
    target_roles = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="Roles this is intended for"
    )
    target_all_staff = models.BooleanField(default=False)

    # Publication
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    published_by_id = models.UUIDField(blank=True, null=True)

    # Validity
    valid_from = models.DateField()
    valid_until = models.DateField(blank=True, null=True)

    # Tracking
    requires_acknowledgment = models.BooleanField(
        default=False,
        help_text="Staff must acknowledge reading"
    )

    # Related Safety Items
    related_occurrences = models.ManyToManyField(
        SafetyOccurrence,
        blank=True,
        related_name='promotions'
    )
    related_hazards = models.ManyToManyField(
        HazardRegister,
        blank=True,
        related_name='promotions'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'safety_promotions'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'published']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.activity_type}: {self.title}"


class SafetyPromotionAcknowledgment(models.Model):
    """
    Staff acknowledgment of safety promotions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    promotion = models.ForeignKey(
        SafetyPromotion,
        on_delete=models.CASCADE,
        related_name='acknowledgments'
    )
    user_id = models.UUIDField()

    acknowledged_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'safety_promotion_acknowledgments'
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['promotion', 'user_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['promotion', 'user_id'],
                name='unique_promotion_acknowledgment'
            )
        ]

    def __str__(self):
        return f"Acknowledgment: {self.user_id} - {self.promotion.title}"


class ChangeManagement(models.Model):
    """
    Management of Change (MOC) for safety-critical changes.

    Per ICAO Doc 9859 Chapter 6:
    - New equipment, procedures, or technology
    - Organizational changes
    - External changes affecting safety
    """

    class ChangeType(models.TextChoices):
        EQUIPMENT = 'equipment', 'Equipment Change'
        PROCEDURE = 'procedure', 'Procedure Change'
        ORGANIZATION = 'organization', 'Organizational Change'
        PERSONNEL = 'personnel', 'Key Personnel Change'
        OPERATIONS = 'operations', 'Operations Change'
        TECHNOLOGY = 'technology', 'Technology Change'
        REGULATORY = 'regulatory', 'Regulatory Requirement'
        EXTERNAL = 'external', 'External Factor'

    class Status(models.TextChoices):
        PROPOSED = 'proposed', 'Proposed'
        UNDER_ASSESSMENT = 'under_assessment', 'Under Assessment'
        APPROVED = 'approved', 'Approved'
        IMPLEMENTING = 'implementing', 'Implementing'
        IMPLEMENTED = 'implemented', 'Implemented'
        MONITORING = 'monitoring', 'Post-Implementation Monitoring'
        CLOSED = 'closed', 'Closed'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Change Details
    change_number = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices
    )

    # Business Case
    reason_for_change = models.TextField()
    benefits = models.TextField(blank=True, null=True)
    alternatives_considered = models.TextField(blank=True, null=True)

    # Scope
    affected_areas = ArrayField(
        models.CharField(max_length=100),
        default=list
    )
    affected_documents = ArrayField(
        models.CharField(max_length=255),
        default=list,
        help_text="Manuals, procedures to be updated"
    )
    affected_personnel = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="Roles/positions affected"
    )

    # Risk Assessment
    safety_risks_identified = models.TextField()
    risk_assessment_completed = models.BooleanField(default=False)

    # Linked hazards from assessment
    identified_hazards = models.ManyToManyField(
        HazardRegister,
        blank=True,
        related_name='from_changes'
    )

    # Implementation
    planned_implementation_date = models.DateField()
    actual_implementation_date = models.DateField(blank=True, null=True)
    implementation_plan = models.TextField(blank=True, null=True)
    rollback_plan = models.TextField(
        blank=True, null=True,
        help_text="How to revert if issues arise"
    )

    # Training Requirements
    training_required = models.BooleanField(default=False)
    training_plan = models.TextField(blank=True, null=True)
    training_completed = models.BooleanField(default=False)

    # Communication
    communication_plan = models.TextField(blank=True, null=True)
    stakeholders_notified = models.BooleanField(default=False)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROPOSED
    )

    # Ownership
    requested_by_id = models.UUIDField()
    change_owner_id = models.UUIDField()

    # Approval
    safety_assessment_by_id = models.UUIDField(blank=True, null=True)
    safety_assessment_date = models.DateField(blank=True, null=True)
    safety_assessment_notes = models.TextField(blank=True, null=True)

    approved_by_id = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)

    # Post-Implementation Review
    review_required_date = models.DateField(
        blank=True, null=True,
        help_text="When to review effectiveness"
    )
    review_completed = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True, null=True)

    # Documentation
    attachments = models.JSONField(default=list)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'change_management'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['change_type']),
            models.Index(fields=['planned_implementation_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'change_number'],
                name='unique_change_number'
            )
        ]

    def __str__(self):
        return f"{self.change_number}: {self.title}"
