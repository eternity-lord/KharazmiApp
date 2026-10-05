# Bug registry — route/API response audit

**Scope:** tests record behavior; no application-code fix is made by this audit. Every open, reproducible issue has a strict `xfail`. Screen-unmapped response candidates or issues depending on an undecided contract remain in `questions.md`; a reproducible server-side correctness/resource-bound defect may still be tracked here when its source comment states an explicit invariant (for example, bounded in-memory conversation history).

## Confirmed/reproducible open findings

| ID | Area / severity | Strict reproduction | Expected | Observed | User-visible consumer / evidence |
|---|---|---|---|---|---|
| O-02 / `RA-auth-02` | Android push capability · high | `test_O02_android_push_client_registers_FCM_token` in `test_known_bugs.py` | Android registers a device token with the backend and has an FCM client. | Kotlin source scan finds neither `FirebaseMessaging` nor `device_token` registration; strict xfail remains. | No push delivery is available from the current Android client; backend device-token route is not a substitute for client registration. |
| O-12 / `RA-exams-02` | Student exam state · medium | `test_O12_unpublished_exam_is_hidden_from_student` | Student list contains only published exams. | `/exams/student/list` includes seeded exam id 2 with `status=pending`; strict xfail remains. | `ExamActivity` / student exam list; source route `Kharazmi_Server/routers/exams.py`. |
| `RA-finance-02` | Server parent-finance route · high | `test_parent_financial_dashboard_accepts_a_valid_parent_session` | A valid parent session resolves its linked child and returns the child finance dashboard. | The same parent's `/homework/parent/child/1` returns 200, but `/finance/parent/dashboard` returns 403. In `routers/finance.py`, the parent handler calls `get_student_financial_dashboard(...)` without forwarding `_role`; the nested handler therefore receives its default `Depends(...)` object in direct Python invocation and `check_student_access` rejects it. Strict xfail. | No matching current Retrofit declaration/screen was found; this is a confirmed broken server route, not an asserted visible Android screen. Source: `finance.py:2122-2129,2234-2255`. |
| `RA-homework-01` | Android/server response contract · medium | `test_parent_homework_wire_items_match_android_display_model` | For a graded parent homework item, the response supplies `max_score` required by `HomeworkItem`. | With the seeded submission temporarily graded at 17, `/homework/parent/child/1` returns the score but omits `max_score`; Gson's non-null `Float` defaults to 0.0. Strict xfail. | `HomeworkNetworkApi.getParentChildHomeworks` → `HomeworkActivity`; the adapter displays `score / max_score` when score is non-null (`HomeworkActivity.kt:221,377-383`). |
| `RA-ai-01` | AI conversation state / memory bound · medium | `test_ai_conversation_history_stays_bounded_to_twelve_messages` in `test_audit_ai.py` | Conversation history stays within a small bounded window; the regression uses 12 stored message entries as the upper bound implied by the route's `len(history) > 10` pre-append guard plus the two entries in a turn. | `/ai/chat` removes at most one history entry before appending two on every later turn; after 20 turns the in-memory history has 26 entries. Strict xfail. No DB write occurs; no current static Android Retrofit caller was found. | `Kharazmi_Server/routers/ai.py:253-268`; source comment says the history volume is limited, but this route has no persistent chat table. |
| `RA-attendance-01` | Live timestamp contract · high | parametrized strict xfail `teacher-current-live` | `started_at_ts` deserializes to Kotlin `Long`. | Seeded `started_at_ts=1790586000.25` is decimal JSON; simulator flags an `int-parse` against `LiveCurrentResponse.startedAtTs`. | `LiveApi.getCurrentLive` → `TeacherDashboardActivity` / `LiveClassActivity`; used for elapsed time. |
| `RA-attendance-02` | Live timestamp contract · high | parametrized strict xfail `admin-live-list` | `started_at_ts` deserializes to Kotlin `Long`. | Same fractional timestamp fails Kotlin Long parsing in `LiveSessionItem`. | `LiveApi.getLiveSessions` → `LiveClassesActivity` and `MainActivity`. |
| `RA-attendance-03` | Live timestamp contract · high | parametrized strict xfail `admin-live-roster` | `started_at_ts` deserializes to Kotlin `Long`. | Same fractional timestamp fails Kotlin Long parsing in `LiveRosterResponse`. | `LiveApi.getLiveRoster` → `LiveRosterActivity`. |
| `RA-teachers-01` | Live timestamp contract · high | parametrized strict xfail `teacher-today-summary` | `live_class.started_at_ts` deserializes to Kotlin `Long`. | Same fractional timestamp fails Kotlin Long parsing in `TeacherTodayLiveClass`. | `TodaySummaryApi.getTeacherTodaySummary` → `TeacherDashboardActivity`; that value is passed to `LiveClassActivity`. |
| O-19 / `RA-admin-19` | Archive restore semantics · medium; product decision pending | `test_O19_restore_class_restores_financial_history_atomically` | The test's proposed full restore expects active enrollments/history to return atomically. | Current implementation is explicitly `metadata_only`; it leaves financial history untouched. Strict xfail retained for traceability, not as permission to silently choose semantics. | Deleted-class restore / finance views. Decision Q-005 remains open. |

## Previously known issue now fixed in this checkout

| ID | Current status | Verification |
|---|---|---|
| O-14 / `RA-parent-01` | **Closed here; not xfailed.** | `ParentExamItem.max_score` is `Float`; the normal test `test_O14_parent_exam_decimal_max_score_is_not_parsed_as_Int` verifies 12.5 without `int-parse`. Android compilation/device execution remains outside this audit. |
| `RA-sweep-01` | Fixed before this audit; normal assertion | Bulk approve response contains non-null `message`; regression pins the specific key. |
| `RA-sweep-02` | Fixed before this audit; normal assertion | Student exam items contain explicit `description` and `due_date`; regression pins those fields. |
| `RA-sweep-03` | Earlier missing `description`/`due_date` issue fixed; normal assertion | Parent homework response contains both fields. A separate graded-state `max_score` omission is recorded as `RA-homework-01`, not mislabeled as the old fix. |
| `RA-sweep-04` | Earlier `students_preview` missing-list issue fixed; normal assertion | Incomplete-class response contains `students_preview: []`. Five other fields of the shared model remain an unresolved Q-006 contract question, not this fixed bug. |
| `RA-admin-01` | Fixed in the current server checkout; normal tests | Dashboard resolves a transaction's student from `Transaction.student_id` when `enrollment_id` is absent. See `test_audit_admin.py` and the admin report. |

## Contract simulator candidates not counted as confirmed bugs

The fresh Kotlin/Gson report is intentionally a **candidate detector**, not a product-bug count. It reports `parse=4`, `npe=5`, and `silent_zero=8`; all candidates were reviewed against current Android call sites before registry classification.

- `GET /finance/student/{id}/dashboard`: `recent_transactions` omits fields required by the broad `TransactionFullItem` model; current `StudentProfileActivity.showCreateInstallmentDialog()` reads only enrollments. **Q-008**; not an xfail.
- `GET /students/my_profile`: `info.parent_mobile` is absent although a shared profile model declares it non-null; current `StudentPortalActivity` displays `name` and `national_code` only. **Q-007**; not an xfail.
- `GET /teachers/{id}/incomplete_classes`: `is_admin_approved`, `is_suspended`, and debt fields are absent from the response while the shared model has defaults. The current incomplete-class dialog reads only `id/title/code`. **Q-006**; not an xfail.
- `GET /homework/parent/child/{student_id}`: `max_score` becomes visible when an item has a score; a separate stateful test promotes that candidate to confirmed `RA-homework-01`.

## Latest isolated route sweep

- **221/221** routes executed; main-request **500 = 0**.
- **220** invalid-target probes; invalid-request **500 = 0**; **11** empty probes, null-list results = 0.
- After correcting probe roles and valid fixtures, the only main-request 403 is `GET /finance/parent/dashboard` with a valid parent session, tracked as `RA-finance-02`.
- Latest full role/status/shape samples are in `tests/route_audit/sweep/report.json`; route-by-route caller/source/DB annotations are in `routes/*.md`.
