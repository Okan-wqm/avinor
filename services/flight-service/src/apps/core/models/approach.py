# services/flight-service/src/apps/core/models/approach.py
"""
Approach Model

Detailed approach tracking for IFR currency.
"""

import uuid
from typing import List, Dict, Any

from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone


class Approach(models.Model):
    """
    Individual approach record for a flight.

    Used for detailed IFR currency tracking and approach type statistics.
    """

    class ApproachType(models.TextChoices):
        ILS = 'ILS', 'ILS'
        ILS_CAT_II = 'ILS_CAT_II', 'ILS CAT II'
        ILS_CAT_III = 'ILS_CAT_III', 'ILS CAT III'
        LOC = 'LOC', 'Localizer'
        LOC_BC = 'LOC_BC', 'Localizer Back Course'
        VOR = 'VOR', 'VOR'
        VOR_DME = 'VOR_DME', 'VOR/DME'
        NDB = 'NDB', 'NDB'
        RNAV_GPS = 'RNAV_GPS', 'RNAV (GPS)'
        RNAV_RNP = 'RNAV_RNP', 'RNAV (RNP)'
        LPV = 'LPV', 'LPV'
        LNAV = 'LNAV', 'LNAV'
        LNAV_VNAV = 'LNAV_VNAV', 'LNAV/VNAV'
        GLS = 'GLS', 'GLS'
        VISUAL = 'VISUAL', 'Visual'
        CONTACT = 'CONTACT', 'Contact'
        CIRCLING = 'CIRCLING', 'Circling'
        SDF = 'SDF', 'SDF'
        LDA = 'LDA', 'LDA'
        ASR = 'ASR', 'ASR (Surveillance)'
        PAR = 'PAR', 'PAR (Precision)'

    class ApproachResult(models.TextChoices):
        LANDED = 'landed', 'Landed'
        MISSED = 'missed', 'Missed Approach'
        CIRCLE_TO_LAND = 'circle_to_land', 'Circle to Land'
        GO_AROUND = 'go_around', 'Go Around'
        TOUCH_AND_GO = 'touch_and_go', 'Touch and Go'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    flight_id = models.UUIDField(db_index=True)
    organization_id = models.UUIDField()

    # ==========================================================================
    # Approach Details
    # ==========================================================================
    approach_type = models.CharField(
        max_length=20,
        choices=ApproachType.choices
    )
    airport_icao = models.CharField(
        max_length=4,
        help_text="Airport ICAO code"
    )
    runway = models.CharField(
        max_length=10,
        help_text="Runway designator (e.g., 05, 27L)"
    )

    # ==========================================================================
    # Approach Execution
    # ==========================================================================
    result = models.CharField(
        max_length=20,
        choices=ApproachResult.choices,
        default=ApproachResult.LANDED
    )

    # Was approach flown in actual IMC?
    in_imc = models.BooleanField(
        default=False,
        help_text="Approach flown in actual IMC"
    )

    # Was it to minimums?
    to_minimums = models.BooleanField(
        default=False,
        help_text="Approach flown to published minimums"
    )

    # Minimum descent altitude/height reached
    lowest_altitude = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Lowest altitude reached (feet AGL)"
    )

    # ==========================================================================
    # Equipment Used
    # ==========================================================================
    coupled = models.BooleanField(
        default=False,
        help_text="Autopilot coupled approach"
    )
    hand_flown = models.BooleanField(
        default=True,
        help_text="Hand flown approach"
    )
    flight_director = models.BooleanField(
        default=False,
        help_text="Flight director used"
    )

    # ==========================================================================
    # Training Specific
    # ==========================================================================
    under_hood = models.BooleanField(
        default=False,
        help_text="Simulated instrument (hood/foggles)"
    )
    safety_pilot_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Safety pilot ID if under hood"
    )

    # ==========================================================================
    # Sequence
    # ==========================================================================
    sequence_number = models.PositiveIntegerField(
        default=1,
        help_text="Approach sequence within the flight"
    )

    # ==========================================================================
    # Notes
    # ==========================================================================
    notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    executed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Time approach was executed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'approaches'
        ordering = ['flight_id', 'sequence_number']
        indexes = [
            models.Index(fields=['flight_id']),
            models.Index(fields=['organization_id', 'approach_type']),
            models.Index(fields=['airport_icao']),
        ]

    def __str__(self):
        return f"{self.approach_type} {self.runway} at {self.airport_icao}"

    @property
    def display_name(self) -> str:
        """Human-readable approach name."""
        return f"{self.get_approach_type_display()} RWY {self.runway} @ {self.airport_icao}"

    @property
    def counts_for_currency(self) -> bool:
        """Check if approach counts for IFR currency."""
        # Visual and contact approaches don't count
        if self.approach_type in [self.ApproachType.VISUAL, self.ApproachType.CONTACT]:
            return False
        return True

    @classmethod
    def get_approach_statistics(
        cls,
        organization_id: uuid.UUID,
        pilot_id: uuid.UUID = None,
        start_date=None,
        end_date=None
    ) -> Dict[str, Any]:
        """Get approach statistics."""
        from .flight import Flight

        # Get flight IDs for the pilot
        flight_query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        )

        if pilot_id:
            flight_query = flight_query.filter(
                models.Q(pic_id=pilot_id) |
                models.Q(sic_id=pilot_id) |
                models.Q(student_id=pilot_id)
            )

        if start_date:
            flight_query = flight_query.filter(flight_date__gte=start_date)

        if end_date:
            flight_query = flight_query.filter(flight_date__lte=end_date)

        flight_ids = flight_query.values_list('id', flat=True)

        # Get approach statistics
        approaches = cls.objects.filter(flight_id__in=flight_ids)

        by_type = approaches.values('approach_type').annotate(
            count=Count('id')
        ).order_by('-count')

        by_airport = approaches.values('airport_icao').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        totals = approaches.aggregate(
            total=Count('id'),
            imc_count=Count('id', filter=models.Q(in_imc=True)),
            to_minimums_count=Count('id', filter=models.Q(to_minimums=True)),
        )

        return {
            'total_approaches': totals['total'] or 0,
            'imc_approaches': totals['imc_count'] or 0,
            'to_minimums': totals['to_minimums_count'] or 0,
            'by_type': list(by_type),
            'by_airport': list(by_airport),
        }


class Hold(models.Model):
    """Holding pattern record."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    flight_id = models.UUIDField(db_index=True)
    organization_id = models.UUIDField()

    # ==========================================================================
    # Hold Details
    # ==========================================================================
    fix_name = models.CharField(
        max_length=10,
        help_text="Holding fix name"
    )
    fix_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="VOR, NDB, intersection, etc."
    )

    # Entry type
    entry_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Direct, teardrop, parallel"
    )

    # Number of turns in hold
    turns = models.PositiveIntegerField(
        default=1,
        help_text="Number of turns in holding pattern"
    )

    # Hold altitude
    altitude = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Holding altitude (feet)"
    )

    # Duration
    duration_minutes = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    # Was it published or ATC assigned?
    published = models.BooleanField(
        default=False,
        help_text="Published holding pattern"
    )

    # In actual IMC?
    in_imc = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)

    executed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'holds'
        ordering = ['flight_id', 'executed_at']

    def __str__(self):
        return f"Hold at {self.fix_name}"
