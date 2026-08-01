"""
Rehearsed fallback record for the defence demo.

Why this exists
---------------
Live extraction needs an LLM API key, a network path to the provider, and a
provider that happens to be healthy. In a defence room, any of the three can
fail, and "the Wi-Fi was down" is not an answer a committee should have to
accept. When demo mode is on and live extraction is unavailable, the extraction
route returns this rehearsed record instead of an error, so the walkthrough of
the verify-and-lock pipeline can still be shown end to end.

Integrity rules this module obeys
---------------------------------
1. **Off by default.** Nothing here is reachable unless ``MAIDA_DEMO_MODE`` is
   explicitly enabled. A production deployment still returns 503.
2. **Never passes as a live extraction.** The record is stamped with
   ``extraction_source="rehearsed_fallback"``, carries an explicit note in
   ``pi_notes``, and is returned with ``requires_verification=True`` so it can
   never be locked without a human decision.
3. **Not a real datum.** The numbers below are illustrative and are deliberately
   NOT taken from the frozen P6 corpus, so a fallback record can never be
   confused with, or silently merged into, the locked analysis set.
"""

from __future__ import annotations

import uuid

from extractor import StatisticalExtractor
from models import StudyDatabaseEntry

FALLBACK_NOTE = (
    "REHEARSED FALLBACK RECORD, NOT A LIVE EXTRACTION. Produced by the demo "
    "fallback path because live extraction was unavailable (no API key, no "
    "network, or provider error). Illustrative values only; not part of the "
    "frozen P6 corpus and not admissible to any analysis."
)


def build_fallback_entry(metadata: dict | None = None) -> StudyDatabaseEntry:
    """Return a rehearsed, clearly-labelled record for the demo walkthrough.

    ``metadata`` may carry whatever bibliographic fields the presenter typed
    into the upload form; they are echoed back so the screen still reflects the
    paper on the projector, while every statistic stays illustrative.
    """
    meta = metadata or {}
    # r is derived from t and df with the pipeline's own documented conversion
    # rather than typed in as a literal, so the rehearsed record stays
    # internally consistent with the formulas the demo is explaining.
    effect_t, effect_df = 2.40, 248
    effect_r = StatisticalExtractor.compute_r_from_t(effect_t, effect_df)
    entry = StudyDatabaseEntry(
        study_id=str(uuid.uuid4()),
        paper_title=str(meta.get("title") or "Rehearsed demo paper (fallback)"),
        authors=str(meta.get("authors") or "Demo, A."),
        year=int(meta.get("year") or 2024),
        country=str(meta.get("country") or "Demo economy"),
        sample_n=250,
        sample_start=2015,
        sample_end=2022,
        effect_t=effect_t,
        effect_df=effect_df,
        effect_r=effect_r,
        p_value=0.017,
        doi_measure="FSTS",
        performance_measure="ACC",
        # Moderator codes are PI-assigned, never machine-proposed, so the
        # fallback leaves them empty rather than inventing a regime label.
        icrv_regime=None,
        cdai_score=None,
        dpl_phase=None,
        # 0.8 is the documented confidence for an effect converted from t,
        # which is what this rehearsed record represents.
        extraction_confidence=0.8,
        df_imputed=False,
        beta_outside_pb_domain=False,
        # Always true: a fallback record must pass through a human decision.
        requires_verification=True,
        pi_locked=False,
        pi_notes=FALLBACK_NOTE,
    )
    entry.machine_proposal = {
        "extraction_source": "rehearsed_fallback",
        "effect_t": entry.effect_t,
        "effect_df": entry.effect_df,
        "effect_r": entry.effect_r,
        "sample_n": entry.sample_n,
        "note": FALLBACK_NOTE,
    }
    return entry
