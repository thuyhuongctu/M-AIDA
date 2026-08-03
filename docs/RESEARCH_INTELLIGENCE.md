# M-AIDA Research Intelligence

`Evidence Atlas` is a descriptive research-diagnostics layer built on top of the human-verified M-AIDA study database. It turns coded records into an evidence geography, an effect landscape, a coverage matrix, and an operational problem radar without replacing the formal meta-analysis.

## What the dashboard communicates

| View | Research question | Interpretation boundary |
|---|---|---|
| Evidence geography | Which location labels are represented? | Describes the loaded database; it is not a global prevalence map. |
| Effect landscape | How are extracted Pearson `r` values distributed? | Individual descriptive points only; it does not display study weights, confidence intervals, heterogeneity, or a pooled effect. |
| Coverage matrix | Which internationalization and performance measures co-occur? | Empty cells are candidate evidence gaps, not proof that the literature contains no studies. |
| Problem radar | Where are verification, missing-data, concentration, and measurement risks visible? | Provides workflow diagnostics; it does not automatically exclude or downgrade a study. |
| Evidence Lens | What patterns deserve the researcher's attention? | Rules-based descriptive text. Human verification remains authoritative. |

The matrix follows the general evidence-and-gap-map principle of organizing evidence across two primary dimensions while permitting characteristics such as location to act as secondary dimensions (Campbell Collaboration, 2020). The effect display follows the visual logic of a forest plot for showing individual-study patterns, but it intentionally omits the summary diamond because M-AIDA has not run a weighted synthesis in this screen (Higgins et al., 2024).

## Integrity rules

1. All visible counts are computed from the records returned by `/api/studies`.
2. No market score, risk score, or AI-generated statistic is invented for visual effect.
3. The displayed mean `r` is explicitly labelled **unweighted and not pooled**.
4. The `−.05` to `+.05` band is a descriptive navigation aid, not a statistical-significance test.
5. PI-locked and review-pending observations remain visually distinct.
6. A map point represents the study's coded location label; it does not establish sample representativeness.
7. The view must evolve with the review protocol and should be reported alongside, not instead of, the PRISMA 2020 record flow and checklist (Page et al., 2021).

## Next research-grade increments

- add a PRISMA 2020 flow view backed by screening-state counts;
- display confidence intervals and study weights after the analysis model exposes them;
- add heterogeneity (`Q`, `I²`, `τ²`) and influence diagnostics only from reproducible model output;
- link matrix cells and map points back to filtered study records;
- add publication-bias views only when the number and independence of effects are methodologically adequate;
- export a figure with dataset version, timestamp, filters, and citation metadata.

## References

Campbell Collaboration. (2020, March 11). *Editorial: Evidence and gap maps*. https://www.campbellcollaboration.org/2020/03/editorial-journal-issue1-2020/

Higgins, J. P. T., Thomas, J., Chandler, J., Cumpston, M., Li, T., Page, M. J., & Welch, V. A. (Eds.). (2024). *Cochrane handbook for systematic reviews of interventions* (Version 6.5). Cochrane. https://www.cochrane.org/handbook

Page, M. J., McKenzie, J. E., Bossuyt, P. M., Boutron, I., Hoffmann, T. C., Mulrow, C. D., Shamseer, L., Tetzlaff, J. M., Akl, E. A., Brennan, S. E., Chou, R., Glanville, J., Grimshaw, J. M., Hróbjartsson, A., Lalu, M. M., Li, T., Loder, E. W., Mayo-Wilson, E., McDonald, S., ... Moher, D. (2021). The PRISMA 2020 statement: An updated guideline for reporting systematic reviews. *BMJ, 372*, n71. https://doi.org/10.1136/bmj.n71
