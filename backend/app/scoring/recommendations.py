"""Retention recommendations — Module 2, Part 2.

Deterministic driver -> intervention lookup. Never LLM-decided: see
MODULE2_REFERENCE.md's "Retention recommendations" section for why (no
network dependency, no hallucination risk, identical driver profiles
always produce identical recommendations, fully auditable). This module
has no LLM call in it at all — the reference doc explicitly calls
skipping LLM involvement a complete, acceptable version of this feature,
and that's the judgment call made here: recommendations ship as clean,
deterministic rule-based text, not run through any prose-polishing step.

`recommend()` operates on `ScoreResult.drivers` — the same top 2-4 driver
list a user is shown in the breakdown (see app/scoring/model.py) — rather
than the full internal candidate set. This is deliberate: a
recommendation should never cite a factor the user can't also see in the
score breakdown, or the two would tell inconsistent stories.

Rules are evaluated in a fixed priority order (documented inline) so
firing is fully deterministic and auditable; several can fire at once
when multiple drivers are independently dominant, which the reference
doc calls more honest than forcing a single answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.scoring.model import DriverContribution, ScoreResult

# A driver only counts as "dominant enough to act on" once it clears the
# midpoint of its own 0-100 sub-scale — i.e. the factor alone would
# already read as medium-or-worse risk in isolation, not just slightly
# above the panel's average.
_DOMINANT_THRESHOLD = 50.0


@dataclass(frozen=True)
class Recommendation:
    key: str
    title: str
    rationale: str


def _risk_points(drivers_by_key: dict[str, DriverContribution], key: str) -> float:
    driver = drivers_by_key.get(key)
    return driver.risk_points if driver is not None else 0.0


def recommend(score_result: ScoreResult) -> list[Recommendation]:
    drivers_by_key = {d.key: d for d in score_result.drivers}

    recognition_gap_triggered = _risk_points(drivers_by_key, "performance_recognition_gap") >= 100.0
    promotion_dominant = _risk_points(drivers_by_key, "promotion_stagnation") >= _DOMINANT_THRESHOLD
    compensation_dominant = _risk_points(drivers_by_key, "compensation_trajectory") >= _DOMINANT_THRESHOLD
    engagement_dominant = _risk_points(drivers_by_key, "engagement") >= _DOMINANT_THRESHOLD
    manager_dominant = _risk_points(drivers_by_key, "manager_effectiveness") >= _DOMINANT_THRESHOLD

    recommendations: list[Recommendation] = []

    # Rule 1 (takes priority over rule 2): a strong performer whose
    # promotion or compensation has stalled is the reference doc's
    # flagship pattern — surface mobility, not just a generic promotion chat.
    if recognition_gap_triggered:
        recommendations.append(
            Recommendation(
                key="career_mobility_conversation",
                title="Career conversation + internal mobility",
                rationale=(
                    "A strong performer with stalled promotion or compensation signals is "
                    "the clearest flight-risk pattern — have a proactive career conversation "
                    "and surface internal mobility options before they look outside."
                ),
            )
        )
    # Rule 2: promotion stagnation on its own, without a confirmed strong-performer signal.
    elif promotion_dominant:
        recommendations.append(
            Recommendation(
                key="promotion_pathing_conversation",
                title="Promotion pathing conversation",
                rationale=(
                    "Promotion timeline has stalled well beyond a typical cycle — discuss "
                    "growth path and set concrete next-step expectations."
                ),
            )
        )

    # Rule 3: compensation, independent of the promotion rules above —
    # both can legitimately fire together.
    if compensation_dominant:
        recommendations.append(
            Recommendation(
                key="compensation_review",
                title="Compensation review",
                rationale=(
                    "Pay is trailing same-grade peers and/or a raise is overdue — trigger a "
                    "compensation review before external offers look more attractive."
                ),
            )
        )

    # Rules 4a/4b/4c: engagement and manager effectiveness are merged into
    # one recommendation when both are dominant (likely the same root
    # cause — the reporting relationship), otherwise handled individually.
    if engagement_dominant and manager_dominant:
        recommendations.append(
            Recommendation(
                key="manager_relationship_conversation",
                title="Manager relationship conversation",
                rationale=(
                    "Low engagement alongside a weak manager-effectiveness signal points at "
                    "the reporting relationship itself — prioritize manager coaching and a "
                    "direct manager-relationship conversation."
                ),
            )
        )
    elif manager_dominant:
        recommendations.append(
            Recommendation(
                key="manager_coaching",
                title="Manager coaching",
                rationale=(
                    "This employee's manager shows a weak effectiveness signal independent of "
                    "the employee's own engagement — flag the manager for coaching support."
                ),
            )
        )
    elif engagement_dominant:
        recommendations.append(
            Recommendation(
                key="engagement_checkin",
                title="Engagement check-in",
                rationale=(
                    "Engagement is low without an accompanying manager-effectiveness signal — "
                    "a direct, non-manager-attributed check-in can help surface the real cause."
                ),
            )
        )

    if not recommendations:
        recommendations.append(
            Recommendation(
                key="monitor",
                title="Monitor — no dominant driver",
                rationale=(
                    "No single factor is currently dominant enough to warrant a targeted "
                    "intervention — continue routine check-ins."
                ),
            )
        )

    return recommendations
