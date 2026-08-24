"""Per-city calibration gates for model and LIMS alert unlocks."""

from dataclasses import dataclass
from datetime import date
from src.serving.alert_state import AlertStateStore, InMemoryAlertStateStore


@dataclass(frozen=True)
class CalibrationReport:
    city_id: str
    feature_days: int
    pinball_p50: float
    pooled_pinball_p50: float
    lims_decile_spread: float
    pooled_lims_decile_spread: float
    attribution_drift: float = 0.0

    @property
    def warmup_complete(self) -> bool:
        return self.feature_days >= 60

    @property
    def pinball_gate(self) -> bool:
        return self.pooled_pinball_p50 > 0 and self.pinball_p50 <= self.pooled_pinball_p50 * 1.10

    @property
    def lims_gate(self) -> bool:
        return self.pooled_lims_decile_spread > 0 and self.lims_decile_spread >= self.pooled_lims_decile_spread * 0.5

    @property
    def attribution_review_required(self) -> bool:
        return self.attribution_drift > 0.25

    @property
    def alert_enabled(self) -> bool:
        return self.warmup_complete and self.pinball_gate and self.lims_gate and not self.attribution_review_required


@dataclass
class CityAlertState:
    """Persistable state machine: new cities remain quiet until calibration passes."""

    city_id: str
    first_feature_date: date | None = None
    enabled: bool = False
    review_reason: str | None = None

    @classmethod
    def load(cls, city_id: str, store: AlertStateStore | None = None) -> "CityAlertState":
        data = (store or InMemoryAlertStateStore()).load(city_id)
        if not data:
            return cls(city_id)
        first = date.fromisoformat(data["first_feature_date"]) if data.get("first_feature_date") else None
        return cls(city_id, first, bool(data.get("enabled", False)), data.get("review_reason"))

    def persist(self, store: AlertStateStore) -> None:
        store.save(self.city_id, {"first_feature_date": self.first_feature_date.isoformat() if self.first_feature_date else None,
                                  "enabled": self.enabled, "review_reason": self.review_reason})

    def observe(self, feature_date: date) -> None:
        if self.first_feature_date is None or feature_date < self.first_feature_date:
            self.first_feature_date = feature_date
        self.enabled = False

    def apply_report(self, report: CalibrationReport) -> bool:
        self.enabled = report.alert_enabled
        self.review_reason = None if self.enabled else self._reason(report)
        return self.enabled

    @staticmethod
    def _reason(report: CalibrationReport) -> str:
        if not report.warmup_complete:
            return "warmup_incomplete"
        if not report.pinball_gate:
            return "pinball_gate_failed"
        if not report.lims_gate:
            return "lims_gate_failed"
        return "attribution_drift_review"


def warmup_days(first_feature_date: date, as_of: date) -> int:
    """Return inclusive feature coverage, clamped at zero for bad timestamps."""
    return max(0, (as_of - first_feature_date).days + 1)


def calibration_report(
    city_id: str,
    first_feature_date: date,
    as_of: date,
    pinball_p50: float,
    pooled_pinball_p50: float,
    lims_decile_spread: float,
    pooled_lims_decile_spread: float,
    attribution_drift: float = 0.0,
) -> CalibrationReport:
    return CalibrationReport(city_id, warmup_days(first_feature_date, as_of), pinball_p50,
                             pooled_pinball_p50, lims_decile_spread, pooled_lims_decile_spread,
                             attribution_drift)
