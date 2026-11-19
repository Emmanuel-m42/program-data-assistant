-- Program tables, metric views and document store for the program data assistant.
-- All data loaded into these tables is fictional.

CREATE EXTENSION IF NOT EXISTS vector;

DROP SCHEMA IF EXISTS program CASCADE;
DROP SCHEMA IF EXISTS docs CASCADE;
CREATE SCHEMA program;
CREATE SCHEMA docs;

SET search_path = program, public;

CREATE TABLE program_settings (
    as_of_date date NOT NULL,
    this_week_start date NOT NULL,
    last_week_start date NOT NULL,
    election_day date NOT NULL,
    gotv_last_knock_day date NOT NULL,
    vr_deadline date NOT NULL,
    overtime_threshold_hours numeric NOT NULL
);

CREATE TABLE offices (
    office text PRIMARY KEY,
    address text NOT NULL,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    opened_on date NOT NULL
);

CREATE TABLE pay_rates (
    role text PRIMARY KEY,
    hourly_rate numeric(6, 2) NOT NULL
);

CREATE TABLE canvassers (
    canvasser_id text PRIMARY KEY,
    full_name text NOT NULL,
    office text NOT NULL REFERENCES offices,
    program text NOT NULL CHECK (program IN ('gotv', 'vr')),
    role text NOT NULL REFERENCES pay_rates,
    start_date date NOT NULL,
    days_worked int NOT NULL
);

CREATE TABLE shifts (
    shift_id text PRIMARY KEY,
    program text NOT NULL CHECK (program IN ('gotv', 'vr')),
    shift_date date NOT NULL,
    canvasser_id text NOT NULL REFERENCES canvassers,
    office text NOT NULL REFERENCES offices,
    clock_in timestamp NOT NULL,
    clock_out timestamp,
    paid_hours numeric(5, 2),
    approval_status text NOT NULL CHECK (approval_status IN ('approved', 'pending', 'needs_fix')),
    fix_note text
);

CREATE TABLE precincts (
    precinct_id text PRIMARY KEY,
    name text NOT NULL,
    office text NOT NULL REFERENCES offices,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    area_sq_mi numeric(7, 3) NOT NULL,
    target_doors int NOT NULL,
    doors_per_sq_mi int NOT NULL
);

CREATE TABLE knocks (
    knock_id text PRIMARY KEY,
    shift_id text NOT NULL REFERENCES shifts,
    canvasser_id text NOT NULL REFERENCES canvassers,
    office text NOT NULL REFERENCES offices,
    precinct_id text NOT NULL REFERENCES precincts,
    knocked_at timestamp NOT NULL,
    address_id text NOT NULL,
    unit text,
    door_id text NOT NULL,
    result text NOT NULL CHECK (result IN ('canvassed', 'not home', 'refused', 'inaccessible')),
    survey_answer text,
    rolled_back boolean NOT NULL
);
CREATE INDEX ON knocks (office, knocked_at);
CREATE INDEX ON knocks (precinct_id);
CREATE INDEX ON knocks (shift_id);

CREATE TABLE daily_goals (
    goal_date date NOT NULL,
    office text NOT NULL REFERENCES offices,
    door_goal int NOT NULL,
    PRIMARY KEY (goal_date, office)
);

CREATE TABLE client_daily_report (
    report_date date NOT NULL,
    office text NOT NULL REFERENCES offices,
    doors_reported int NOT NULL,
    contacts_reported int NOT NULL,
    PRIMARY KEY (report_date, office)
);

CREATE TABLE qc_flags (
    flag_id text PRIMARY KEY,
    shift_id text NOT NULL REFERENCES shifts,
    canvasser_id text NOT NULL REFERENCES canvassers,
    office text NOT NULL REFERENCES offices,
    flag_date date NOT NULL,
    flag_type text NOT NULL CHECK (flag_type IN ('flash_knocking', 'householding', 'gap')),
    evidence text NOT NULL,
    evidence_start timestamp NOT NULL,
    evidence_end timestamp NOT NULL,
    knock_count int NOT NULL,
    status text NOT NULL CHECK (status IN ('open', 'reviewed')),
    knocks_rolled_back boolean NOT NULL
);

CREATE TABLE candidate_office_sites (
    site_id text PRIMARY KEY,
    name text NOT NULL,
    address text NOT NULL,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    monthly_rent int NOT NULL
);

CREATE TABLE vr_goals (
    office text PRIMARY KEY REFERENCES offices,
    card_goal int NOT NULL
);

CREATE TABLE vr_cards (
    card_id text PRIMARY KEY,
    shift_id text NOT NULL REFERENCES shifts,
    canvasser_id text NOT NULL REFERENCES canvassers,
    office text NOT NULL REFERENCES offices,
    collected_at timestamp NOT NULL,
    registrant_name text NOT NULL,
    duplicate_group_id text,
    is_duplicate boolean NOT NULL
);

CREATE TABLE vr_qc_calls (
    call_id text PRIMARY KEY,
    card_id text NOT NULL REFERENCES vr_cards,
    called_at timestamp NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('confirmed', 'unreachable', 'wrong_info'))
);

-- Great-circle distance in kilometers.
CREATE FUNCTION km_between(lat1 double precision, lon1 double precision, lat2 double precision, lon2 double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE AS $$
    SELECT 6371 * 2 * asin(sqrt(power(sin(radians(lat2 - lat1) / 2), 2)
        + cos(radians(lat1)) * cos(radians(lat2)) * power(sin(radians(lon2 - lon1) / 2), 2)))
$$;

-- ---------- metric views ----------

-- One row per office per knocking day. A door is one door_id knocked on one day (rollbacks excluded).
CREATE VIEW v_daily_doors AS
SELECT knocked_at::date AS knock_date,
       office,
       count(DISTINCT door_id) FILTER (WHERE NOT rolled_back) AS doors,
       count(*) FILTER (WHERE NOT rolled_back AND result = 'canvassed') AS contacts,
       count(*) AS attempts,
       count(*) FILTER (WHERE rolled_back) AS rolled_back_attempts
FROM knocks
GROUP BY 1, 2;

-- Door pace and projection per office, plus an 'All offices' total row.
CREATE VIEW v_office_pace AS
WITH s AS (SELECT * FROM program_settings),
d AS (
    SELECT v.office,
           sum(v.doors) AS doors_to_date,
           sum(v.doors) FILTER (WHERE v.knock_date > s.as_of_date - 7) AS doors_last_7d
    FROM v_daily_doors v, s GROUP BY v.office
),
g AS (
    SELECT office, sum(door_goal) AS goal_total,
           sum(door_goal) FILTER (WHERE goal_date <= (SELECT as_of_date FROM s)) AS goal_to_date
    FROM daily_goals GROUP BY office
),
sh AS (
    SELECT office, count(*) FILTER (WHERE shift_date > (SELECT as_of_date FROM s) - 7) AS shifts_last_7d
    FROM shifts WHERE program = 'gotv' GROUP BY office
),
o AS (
    SELECT d.office, g.goal_total, g.goal_to_date, d.doors_to_date, d.doors_last_7d, sh.shifts_last_7d,
           (s.gotv_last_knock_day - s.as_of_date) AS knocking_days_left
    FROM d JOIN g USING (office) JOIN sh USING (office), s
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', sum(goal_total), sum(goal_to_date), sum(doors_to_date), sum(doors_last_7d), sum(shifts_last_7d),
           max(knocking_days_left)
    FROM o
)
SELECT office,
       goal_total,
       goal_to_date,
       doors_to_date,
       round(100.0 * doors_to_date / goal_to_date, 1) AS pct_of_goal_to_date,
       round(doors_last_7d / 7.0, 1) AS avg_daily_doors_last_7d,
       knocking_days_left,
       round(doors_to_date + doors_last_7d / 7.0 * knocking_days_left) AS projected_total,
       round(doors_to_date + doors_last_7d / 7.0 * knocking_days_left - goal_total) AS projected_vs_goal,
       round(100.0 * (doors_to_date + doors_last_7d / 7.0 * knocking_days_left) / goal_total, 1) AS projected_pct_of_goal,
       round(shifts_last_7d / 7.0, 1) AS avg_shifts_per_day_last_7d,
       round(doors_last_7d::numeric / shifts_last_7d, 1) AS doors_per_shift_last_7d,
       round(greatest(goal_total - doors_to_date, 0) / knocking_days_left::numeric / (doors_last_7d::numeric / shifts_last_7d), 1)
           AS shifts_per_day_needed,
       round(greatest(greatest(goal_total - doors_to_date, 0) / knocking_days_left::numeric / (doors_last_7d::numeric / shifts_last_7d)
           - shifts_last_7d / 7.0, 0), 1) AS extra_shifts_per_day_needed
FROM u;

-- Turf coverage per precinct. Touched = door_id knocked at least once (rollbacks excluded).
CREATE VIEW v_precinct_coverage AS
SELECT p.precinct_id, p.name, p.office, p.target_doors,
       coalesce(t.doors_touched, 0) AS doors_touched,
       p.target_doors - coalesce(t.doors_touched, 0) AS doors_untouched,
       round(100.0 * coalesce(t.doors_touched, 0) / p.target_doors, 1) AS pct_touched,
       coalesce(t.not_home_doors, 0) AS not_home_doors,
       p.doors_per_sq_mi, p.area_sq_mi,
       round(km_between(p.lat, p.lon, o.lat, o.lon)::numeric, 2) AS km_to_office,
       CASE WHEN coalesce(t.doors_touched, 0) = 0 THEN 'untouched'
            WHEN 100.0 * t.doors_touched / p.target_doors < 25 THEN 'light'
            WHEN 100.0 * t.doors_touched / p.target_doors < 90 THEN 'partial'
            ELSE 'covered' END AS coverage,
       p.lat, p.lon
FROM precincts p
JOIN offices o USING (office)
LEFT JOIN (
    SELECT precinct_id, count(DISTINCT door_id) AS doors_touched,
           count(*) FILTER (WHERE last_result = 'not home') AS not_home_doors
    FROM (SELECT DISTINCT ON (door_id) precinct_id, door_id, result AS last_result
          FROM knocks WHERE NOT rolled_back ORDER BY door_id, knocked_at DESC) k
    GROUP BY precinct_id
) t USING (precinct_id);

-- Candidate sites for a new office, scored against the doors still untouched.
CREATE VIEW v_site_options AS
SELECT s.site_id, s.name, s.address, s.monthly_rent,
       round((sum(c.doors_untouched * km_between(s.lat, s.lon, c.lat, c.lon)) / nullif(sum(c.doors_untouched), 0))::numeric, 2)
           AS avg_km_to_untouched_doors,
       coalesce(sum(c.doors_untouched) FILTER (WHERE km_between(s.lat, s.lon, c.lat, c.lon) <= 3), 0) AS untouched_doors_within_3km,
       (SELECT round(min(km_between(s.lat, s.lon, o.lat, o.lon))::numeric, 2) FROM offices o) AS km_to_nearest_office
FROM candidate_office_sites s CROSS JOIN v_precinct_coverage c
GROUP BY s.site_id, s.name, s.address, s.monthly_rent, s.lat, s.lon;

-- Registration pace per office plus an 'All offices' row. Valid cards exclude duplicates.
CREATE VIEW v_vr_pace AS
WITH s AS (SELECT * FROM program_settings),
c AS (
    SELECT office, count(*) AS cards_collected,
           count(*) FILTER (WHERE is_duplicate) AS duplicate_cards,
           count(*) FILTER (WHERE NOT is_duplicate) AS valid_cards,
           count(*) FILTER (WHERE NOT is_duplicate AND collected_at::date > (SELECT as_of_date FROM s) - 7) AS valid_cards_last_7d
    FROM vr_cards GROUP BY office
),
h AS (
    SELECT office, sum(paid_hours) AS hours_to_date,
           sum(paid_hours) FILTER (WHERE shift_date > (SELECT as_of_date FROM s) - 7) AS hours_last_7d
    FROM shifts WHERE program = 'vr' GROUP BY office
),
o AS (
    SELECT office, g.card_goal, c.cards_collected, c.duplicate_cards, c.valid_cards, c.valid_cards_last_7d,
           h.hours_to_date, h.hours_last_7d, (s.vr_deadline - s.as_of_date) AS days_left
    FROM c JOIN h USING (office) JOIN vr_goals g USING (office), s
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', sum(card_goal), sum(cards_collected), sum(duplicate_cards), sum(valid_cards), sum(valid_cards_last_7d),
           sum(hours_to_date), sum(hours_last_7d), max(days_left)
    FROM o
)
SELECT office, card_goal, cards_collected, duplicate_cards, valid_cards,
       card_goal - valid_cards AS cards_remaining,
       hours_to_date,
       round(valid_cards / hours_to_date, 2) AS cards_per_hour_to_date,
       round(valid_cards_last_7d / hours_last_7d, 2) AS cards_per_hour_last_7d,
       round(hours_last_7d / 7.0, 1) AS avg_daily_hours_last_7d,
       days_left,
       round(valid_cards + valid_cards_last_7d / 7.0 * days_left) AS projected_valid_cards,
       round(greatest(card_goal - valid_cards, 0) / (hours_last_7d / 7.0 * days_left), 2) AS cards_per_hour_needed
FROM u;

-- Paid hours per person per week (Monday start). needs_fix shifts with no clock out have no paid hours yet.
CREATE VIEW v_weekly_hours AS
SELECT c.canvasser_id, c.full_name, c.office, c.program,
       date_trunc('week', sh.shift_date)::date AS week_start,
       count(*) AS shifts,
       sum(sh.paid_hours) AS paid_hours,
       count(*) FILTER (WHERE sh.approval_status = 'pending') AS shifts_pending,
       count(*) FILTER (WHERE sh.approval_status = 'needs_fix') AS shifts_needs_fix,
       coalesce(sum(sh.paid_hours), 0) > (SELECT overtime_threshold_hours FROM program_settings) AS over_threshold
FROM shifts sh JOIN canvassers c USING (canvasser_id)
GROUP BY 1, 2, 3, 4, 5;

-- QC flags per office per week, with the rate per 100 GOTV shifts.
CREATE VIEW v_qc_weekly AS
WITH sh AS (
    SELECT office, date_trunc('week', shift_date)::date AS week_start, count(*) AS shifts
    FROM shifts WHERE program = 'gotv' GROUP BY 1, 2
),
f AS (
    SELECT office, date_trunc('week', flag_date)::date AS week_start, count(*) AS flags,
           count(*) FILTER (WHERE flag_type = 'flash_knocking') AS flash_knocking,
           count(*) FILTER (WHERE flag_type = 'householding') AS householding,
           count(*) FILTER (WHERE flag_type = 'gap') AS gaps
    FROM qc_flags GROUP BY 1, 2
)
SELECT sh.office, sh.week_start, sh.shifts,
       coalesce(f.flags, 0) AS flags,
       coalesce(f.flash_knocking, 0) AS flash_knocking,
       coalesce(f.householding, 0) AS householding,
       coalesce(f.gaps, 0) AS gaps,
       round(100.0 * coalesce(f.flags, 0) / sh.shifts, 1) AS flags_per_100_shifts
FROM sh LEFT JOIN f USING (office, week_start);

-- ---------- helper views for common questions ----------

-- Contact rate per office per week (Monday start), plus 'All offices'.
CREATE VIEW v_contact_rates AS
WITH w AS (
    SELECT office, date_trunc('week', knock_date)::date AS week_start, sum(doors) AS doors, sum(contacts) AS contacts
    FROM v_daily_doors GROUP BY 1, 2
),
u AS (
    SELECT * FROM w
    UNION ALL
    SELECT 'All offices', week_start, sum(doors), sum(contacts) FROM w GROUP BY week_start
)
SELECT office, week_start, doors, contacts, round(100.0 * contacts / doors, 1) AS contact_rate_pct FROM u;

-- GOTV wages and cost per door to date, plus 'All offices'.
CREATE VIEW v_cost_per_door AS
WITH p AS (
    SELECT s.office, sum(s.paid_hours) AS paid_hours, sum(s.paid_hours * r.hourly_rate) AS wages
    FROM shifts s JOIN canvassers c USING (canvasser_id) JOIN pay_rates r USING (role)
    WHERE s.program = 'gotv' GROUP BY s.office
),
d AS (SELECT office, sum(doors) AS doors FROM v_daily_doors GROUP BY office),
u AS (
    SELECT p.office, p.paid_hours, p.wages, d.doors FROM p JOIN d USING (office)
    UNION ALL
    SELECT 'All offices', sum(p.paid_hours), sum(p.wages), sum(d.doors) FROM p JOIN d USING (office)
)
SELECT office, paid_hours, round(wages, 2) AS wages, doors, round(wages / doors, 2) AS cost_per_door FROM u;

-- The weekly client report: doors, contacts, valid cards and paid hours per office per week.
CREATE VIEW v_weekly_report AS
WITH d AS (
    SELECT office, date_trunc('week', knock_date)::date AS week_start, sum(doors) AS doors, sum(contacts) AS contacts
    FROM v_daily_doors GROUP BY 1, 2
),
c AS (
    SELECT office, date_trunc('week', collected_at)::date AS week_start, count(*) FILTER (WHERE NOT is_duplicate) AS valid_cards
    FROM vr_cards GROUP BY 1, 2
),
h AS (
    SELECT office, date_trunc('week', shift_date)::date AS week_start, sum(paid_hours) AS paid_hours,
           count(*) FILTER (WHERE clock_out IS NULL) AS shifts_missing_clock_out
    FROM shifts GROUP BY 1, 2
),
o AS (
    SELECT office, week_start, d.doors, d.contacts, coalesce(c.valid_cards, 0) AS valid_cards, h.paid_hours,
           h.shifts_missing_clock_out
    FROM h LEFT JOIN d USING (office, week_start) LEFT JOIN c USING (office, week_start)
)
SELECT * FROM o
UNION ALL
SELECT 'All offices', week_start, sum(doors), sum(contacts), sum(valid_cards), sum(paid_hours), sum(shifts_missing_clock_out)
FROM o GROUP BY week_start;

-- One row per person with how much they have worked and whether they are active and regular.
CREATE VIEW v_canvasser_status AS
SELECT c.canvasser_id, c.full_name, c.office, c.program, c.role,
       count(DISTINCT s.shift_date) AS days_worked,
       min(s.shift_date) AS first_shift, max(s.shift_date) AS last_shift,
       max(s.shift_date) > (SELECT as_of_date FROM program_settings) - 7 AS active,
       CASE WHEN count(DISTINCT s.shift_date) >= 5 THEN 'regular'
            WHEN count(DISTINCT s.shift_date) = 1 THEN 'one-day hire'
            ELSE 'occasional' END AS staff_type
FROM canvassers c JOIN shifts s USING (canvasser_id)
GROUP BY c.canvasser_id, c.full_name, c.office, c.program, c.role;

-- QC flags with the canvasser's name.
CREATE VIEW v_qc_flags_detail AS
SELECT f.flag_id, f.flag_date, f.office, f.canvasser_id, c.full_name, f.shift_id, f.flag_type, f.status, f.evidence,
       f.evidence_start, f.evidence_end, f.knock_count, f.knocks_rolled_back
FROM qc_flags f JOIN canvassers c USING (canvasser_id);

-- Shifts that are not approved yet, with the reason.
CREATE VIEW v_shifts_to_fix AS
SELECT s.shift_id, s.shift_date, date_trunc('week', s.shift_date)::date AS week_start, c.full_name, s.office, s.program,
       s.approval_status, s.fix_note, s.paid_hours
FROM shifts s JOIN canvassers c USING (canvasser_id)
WHERE s.approval_status <> 'approved';

-- Registration results per registration canvasser.
CREATE VIEW v_vr_canvassers AS
SELECT c.canvasser_id, c.full_name, c.office,
       count(v.card_id) AS cards_collected,
       count(v.card_id) FILTER (WHERE v.is_duplicate) AS duplicate_cards,
       round(100.0 * count(v.card_id) FILTER (WHERE v.is_duplicate) / nullif(count(v.card_id), 0), 1) AS duplicate_rate_pct,
       count(q.call_id) AS qc_calls,
       count(q.call_id) FILTER (WHERE q.outcome = 'confirmed') AS qc_confirmed,
       count(q.call_id) FILTER (WHERE q.outcome = 'unreachable') AS qc_unreachable,
       count(q.call_id) FILTER (WHERE q.outcome = 'wrong_info') AS qc_wrong_info
FROM canvassers c
JOIN vr_cards v USING (canvasser_id)
LEFT JOIN vr_qc_calls q USING (card_id)
WHERE c.program = 'vr'
GROUP BY c.canvasser_id, c.full_name, c.office;

-- Registration QC call outcomes per office, plus 'All offices'.
CREATE VIEW v_qc_call_outcomes AS
WITH o AS (
    SELECT v.office, q.outcome, count(*) AS calls FROM vr_qc_calls q JOIN vr_cards v USING (card_id) GROUP BY 1, 2
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', outcome, sum(calls) FROM o GROUP BY outcome
)
SELECT office, outcome, calls, round(100.0 * calls / sum(calls) OVER (PARTITION BY office), 1) AS share_pct FROM u;

-- ---------- documents ----------

CREATE TABLE docs.documents (
    doc_id text PRIMARY KEY,
    title text NOT NULL,
    path text NOT NULL
);

CREATE TABLE docs.chunks (
    chunk_id text PRIMARY KEY,
    doc_id text NOT NULL REFERENCES docs.documents,
    heading text NOT NULL,
    text text NOT NULL,
    embedding vector(384) NOT NULL
);

-- ---------- read-only role for the SQL tool ----------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pda_reader') THEN
        CREATE ROLE pda_reader LOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA program TO pda_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA program TO pda_reader;
ALTER ROLE pda_reader SET search_path = program;
ALTER ROLE pda_reader SET default_transaction_read_only = on;
ALTER ROLE pda_reader SET statement_timeout = '5s';
