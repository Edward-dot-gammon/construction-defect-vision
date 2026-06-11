# Labeling Protocol

Version: **1.0**  
Status: **Active**

This document defines how inspection photos are labeled for training the image-only defect classifier. Labels use inspection metadata during dataset creation; metadata is **not** available at inference.

---

## Locked decisions

| Decision | Choice | Date |
|----------|--------|------|
| **Stage-dependent image policy** | **Exclude** | 2026-06-10 |
| Label granularity | Image level | — |
| Supervised label classes | `defect`, `no_defect` only | — |
| Review class | `uncertain_requires_human_review` (excluded from training until resolved) | — |

---

## Stage-dependent image policy: Exclude

**Policy:** If whether a photo is acceptable depends on work stage and cannot be inferred from pixels alone, **omit the image from the supervised training set**.

### Rationale

The deployed model receives a single photo with no RFI text or work description. Images whose acceptability depends on stage (e.g. standing water during a flooding test before waterproofing) would teach misleading defect/no-defect signals. Excluding them keeps the supervised set aligned with image-only learning.

### How to identify stage-dependent images

Mark as stage-dependent when **all** of the following apply:

1. The visual could be read as either acceptable or defective depending on `description_of_works` or `subsequent_work`.
2. A reviewer cannot assign `defect` or `no_defect` from the image alone without reading inspection metadata.
3. The image is not an obvious structural defect (crack, spalling, etc.) visible regardless of work stage.

### Examples

| Scenario | Stage-dependent? | Action |
|----------|------------------|--------|
| Water ponded on slab during flooding test before waterproofing | Yes | **Exclude** |
| Crack in hardened concrete (visible fracture) | No | Label `defect` or `no_defect` from image |
| Fresh pour with normal bleed water vs defective pooling | Often yes | **Exclude** if ambiguous without stage context |
| Structural drawing sheet | N/A (not a site photo) | **Exclude** — `filter_reason: drawing` |
| Logo or stamp | N/A | **Exclude** — `filter_reason: logo` |

### Fields to set when excluding

```json
{
  "stage_policy": "exclude",
  "filter_reason": "stage_dependent",
  "label": null,
  "review_status": "excluded_from_training"
}
```

Excluded images remain in the manifest for audit and may be revisited if policy changes or work-type stratification is added later.

### What we are not doing (for now)

- **Uncertain** as default for stage-dependent cases — reserved for genuinely ambiguous images that are not clearly stage-dependent.
- **Stratify** by `work_type` — deferred until enough labeled data exists per work category.

---

## Label classes

### Supervised training (Phase 2+)

Only these labels enter classifier training:

| Label | Meaning |
|-------|---------|
| `defect` | Visible construction defect or quality non-conformance |
| `no_defect` | No defect apparent from the image alone |

### Review queue (not trained until resolved)

| Label | Meaning |
|-------|---------|
| `uncertain_requires_human_review` | Ambiguous on visual grounds; not used for stage-dependent exclusion |

---

## Label granularity

- One label per **image** (`image_id`).
- Inspection metadata (`InspectionRecord`) is **context for labeling**, not the label itself.
- Record `work_type` (derived from `description_of_works`) on each `TrainingLabel` for error analysis.

---

## Issue annotation (defect only)

When `label` is `defect`, also record:

| Field | Description |
|-------|-------------|
| `issue_type` | e.g. `crack`, `spalling`, `water_stain`, `misalignment`, `incomplete_work`, `corrosion`, `other` |
| `severity` | `low`, `medium`, `high` |
| `short_reason` | One-line summary for reviewers |
| `visible_evidence` | What is visible in the image supporting the label |

---

## Weak supervision (bootstrap only)

Inspector outcome may suggest a provisional label during dataset build:

| Signal | Provisional hint | Trust level |
|--------|------------------|-------------|
| Accepted, no comments | `no_defect` | Low — human review required |
| Rejected with defect comments | `defect` | Medium — confirm against image |
| Conditionally accepted | Review manually | Do not auto-label |

Set `label_source`: `weak_supervision` for bootstrapped labels; `human` after reviewer confirmation.

**Inspector outcome is not ground truth.** Photos can be accepted with unphotographed defects, or rejected for non-visual reasons.

---

## Image type filtering

Apply before or during `dataset/builder.py`. Non-site photos are excluded from training:

| `image_type` | `filter_reason` | Training |
|--------------|-----------------|----------|
| `site_photo` | — | Eligible if not stage-dependent |
| `drawing` | `drawing` | Excluded |
| `logo` | `logo` | Excluded |
| `stamp` | `stamp` | Excluded |
| `low_information` | `low_information` | Excluded |
| `duplicate` | `duplicate` | Excluded |

---

## Borderline handling

| Situation | Action |
|-----------|--------|
| Stage-dependent (needs work context) | **Exclude** — `stage_policy: exclude`, `filter_reason: stage_dependent` |
| Visually ambiguous, not stage-dependent | `uncertain_requires_human_review` |
| Clear defect or no defect from image alone | `defect` or `no_defect` |

---

## Reviewer policy

1. Reviewers may override any label and add `notes`.
2. Overrides are stored with `label_source: human` and logged as `AuditEvent`.
3. Corrections feed future re-labeling and Phase 4 re-training.
4. Excluded (stage-dependent) images may be promoted to supervised labels only if policy changes and the image is re-reviewed.

---

## Dataset builder rules (summary)

Include in supervised manifest **only** when:

- `image_type` is `site_photo`
- `filter_reason` is null
- `stage_policy` is not `exclude` (or `stage_policy` is `supervised`)
- `label` is `defect` or `no_defect`
- `review_status` is `confirmed` (or `label_source: human`)

Exclude from supervised manifest when:

- `filter_reason` is set (drawing, logo, stage_dependent, etc.)
- `stage_policy` is `exclude`
- `label` is `uncertain_requires_human_review` or null

---

## Version history

| Version | Change |
|---------|--------|
| 1.0 | Initial protocol; stage-dependent policy locked to **Exclude** |
