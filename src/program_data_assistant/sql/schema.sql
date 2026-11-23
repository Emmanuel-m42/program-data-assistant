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

-- Program totals live in separate *_total views, never as extra rows in an office view: a model that adds up an
-- office view's rows must get the program total, not twice it. Each all_* view below builds the office rows and the
-- 'All offices' rows together (so both come from one definition) and is split into v_<name> (offices only) and
-- v_<name>_total (the 'All offices' rows). The all_* views are not on the SQL tool's allow list.

-- One row per office per knocking day; v_daily_doors_total has one row per day. A door is one door_id knocked on one
-- day (rollbacks excluded).
CREATE VIEW all_daily_doors AS
WITH o AS (
    SELECT knocked_at::date AS knock_date,
           office,
           count(DISTINCT door_id) FILTER (WHERE NOT rolled_back) AS doors,
           count(*) FILTER (WHERE NOT rolled_back AND result = 'canvassed') AS contacts,
           count(*) AS attempts,
           count(*) FILTER (WHERE rolled_back) AS rolled_back_attempts
    FROM knocks
    GROUP BY 1, 2
)
SELECT * FROM o
UNION ALL
SELECT knock_date, 'All offices', sum(doors)::bigint, sum(contacts)::bigint, sum(attempts)::bigint,
       sum(rolled_back_attempts)::bigint
FROM o GROUP BY knock_date;
CREATE VIEW v_daily_doors AS SELECT * FROM all_daily_doors WHERE office <> 'All offices';
CREATE VIEW v_daily_doors_total AS SELECT * FROM all_daily_doors WHERE office = 'All offices';

-- Door pace and projection per office (v_office_pace_total: the program). doors_untouched is every turf door never
-- knocked (rollbacks removed), in every precinct, including the untouched doors of partly covered precincts.
CREATE VIEW all_office_pace AS
WITH s AS (SELECT * FROM program_settings),
d AS (
    SELECT v.office,
           sum(v.doors) AS doors_to_date,
           sum(v.doors) FILTER (WHERE v.knock_date > s.as_of_date - 7) AS doors_last_7d
    FROM v_daily_doors v, s GROUP BY v.office
),
t AS (
    SELECT p.office, p.turf_doors, coalesce(k.doors_touched, 0) AS doors_touched
    FROM (SELECT office, sum(target_doors) AS turf_doors FROM precincts GROUP BY office) p
    LEFT JOIN (SELECT office, count(DISTINCT door_id) AS doors_touched FROM knocks WHERE NOT rolled_back GROUP BY office) k
        USING (office)
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
           (s.gotv_last_knock_day - s.as_of_date) AS knocking_days_left, t.turf_doors, t.doors_touched
    FROM d JOIN g USING (office) JOIN sh USING (office) JOIN t USING (office), s
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', sum(goal_total), sum(goal_to_date), sum(doors_to_date), sum(doors_last_7d), sum(shifts_last_7d),
           max(knocking_days_left), sum(turf_doors), sum(doors_touched)
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
           - shifts_last_7d / 7.0, 0), 1) AS extra_shifts_per_day_needed,
       turf_doors,
       turf_doors - doors_touched AS doors_untouched,
       doors_touched,
       round(100.0 * doors_touched / turf_doors, 1) AS pct_turf_touched,
       round(100.0 * doors_to_date / goal_total, 1) AS pct_of_goal_total,
       round(doors_last_7d / 7.0 * knocking_days_left) AS capacity_days_left
FROM u;
CREATE VIEW v_office_pace AS SELECT * FROM all_office_pace WHERE office <> 'All offices';
CREATE VIEW v_office_pace_total AS SELECT * FROM all_office_pace WHERE office = 'All offices';

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

-- Registration pace per office (v_vr_pace_total: the program). Valid cards exclude duplicates.
CREATE VIEW all_vr_pace AS
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
       round(100.0 * valid_cards / card_goal, 1) AS pct_of_card_goal,
       hours_to_date,
       round(valid_cards / hours_to_date, 2) AS cards_per_hour_to_date,
       round(valid_cards_last_7d / hours_last_7d, 2) AS cards_per_hour_last_7d,
       round(hours_last_7d / 7.0, 1) AS avg_daily_hours_last_7d,
       days_left,
       round(valid_cards + valid_cards_last_7d / 7.0 * days_left) AS projected_valid_cards,
       round(greatest(card_goal - valid_cards, 0) / (hours_last_7d / 7.0 * days_left), 2) AS cards_per_hour_needed
FROM u;
CREATE VIEW v_vr_pace AS SELECT * FROM all_vr_pace WHERE office <> 'All offices';
CREATE VIEW v_vr_pace_total AS SELECT * FROM all_vr_pace WHERE office = 'All offices';

-- Paid hours and wages per person per week (Monday start). A shift with no clock out has no paid hours yet:
-- shifts_with_hours counts the shifts that have them. wages = paid hours x the person's hourly rate.
CREATE VIEW v_weekly_hours AS
SELECT c.canvasser_id, c.full_name, c.office, c.program, c.role,
       date_trunc('week', sh.shift_date)::date AS week_start,
       count(*) AS shifts,
       count(sh.paid_hours) AS shifts_with_hours,
       sum(sh.paid_hours) AS paid_hours,
       round(sum(sh.paid_hours * r.hourly_rate), 2) AS wages,
       count(*) FILTER (WHERE sh.approval_status = 'pending') AS shifts_pending,
       count(*) FILTER (WHERE sh.approval_status = 'needs_fix') AS shifts_needs_fix,
       coalesce(sum(sh.paid_hours), 0) > (SELECT overtime_threshold_hours FROM program_settings) AS over_threshold
FROM shifts sh JOIN canvassers c USING (canvasser_id) JOIN pay_rates r USING (role)
GROUP BY 1, 2, 3, 4, 5, 6;

-- Shifts, paid hours, shift length and wages per office, program and week (v_weekly_shifts_total: all offices).
-- Shift length = paid hours / shifts with a clock out; a shift with no clock out has no length yet.
CREATE VIEW all_weekly_shifts AS
WITH o AS (
    SELECT s.office, s.program, date_trunc('week', s.shift_date)::date AS week_start,
           count(*) AS shifts, count(s.paid_hours) AS shifts_with_hours,
           count(*) FILTER (WHERE s.clock_out IS NULL) AS shifts_missing_clock_out,
           sum(s.paid_hours) AS paid_hours, sum(s.paid_hours * r.hourly_rate) AS wages
    FROM shifts s JOIN canvassers c USING (canvasser_id) JOIN pay_rates r USING (role)
    GROUP BY 1, 2, 3
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', program, week_start, sum(shifts)::bigint, sum(shifts_with_hours)::bigint,
           sum(shifts_missing_clock_out)::bigint, sum(paid_hours), sum(wages)
    FROM o GROUP BY program, week_start
)
SELECT office, program, week_start, shifts, shifts_with_hours, shifts_missing_clock_out, paid_hours,
       round(paid_hours / nullif(shifts_with_hours, 0), 2) AS avg_shift_hours, round(wages, 2) AS wages
FROM u;
CREATE VIEW v_weekly_shifts AS SELECT * FROM all_weekly_shifts WHERE office <> 'All offices';
CREATE VIEW v_weekly_shifts_total AS SELECT * FROM all_weekly_shifts WHERE office = 'All offices';

-- Doors against the door goal per office per week (v_weekly_pace_total: all offices).
CREATE VIEW all_weekly_pace AS
WITH g AS (
    SELECT office, date_trunc('week', goal_date)::date AS week_start, sum(door_goal) AS door_goal
    FROM daily_goals WHERE goal_date <= (SELECT as_of_date FROM program_settings) GROUP BY 1, 2
),
d AS (
    SELECT office, date_trunc('week', knock_date)::date AS week_start, sum(doors) AS doors, sum(contacts) AS contacts
    FROM v_daily_doors GROUP BY 1, 2
),
o AS (SELECT office, week_start, g.door_goal, coalesce(d.doors, 0) AS doors, coalesce(d.contacts, 0) AS contacts
      FROM g LEFT JOIN d USING (office, week_start)),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', week_start, sum(door_goal), sum(doors), sum(contacts) FROM o GROUP BY week_start
)
SELECT office, week_start, door_goal, doors, contacts, doors - door_goal AS doors_vs_goal,
       round(100.0 * doors / door_goal, 1) AS pct_of_goal
FROM u;
CREATE VIEW v_weekly_pace AS SELECT * FROM all_weekly_pace WHERE office <> 'All offices';
CREATE VIEW v_weekly_pace_total AS SELECT * FROM all_weekly_pace WHERE office = 'All offices';

-- Registration cards and hours per office per week (v_vr_weekly_total: all offices). Valid cards exclude duplicates.
CREATE VIEW all_vr_weekly AS
WITH c AS (
    SELECT office, date_trunc('week', collected_at)::date AS week_start,
           count(*) FILTER (WHERE NOT is_duplicate) AS valid_cards, count(*) FILTER (WHERE is_duplicate) AS duplicate_cards
    FROM vr_cards GROUP BY 1, 2
),
h AS (
    SELECT office, date_trunc('week', shift_date)::date AS week_start, sum(paid_hours) AS paid_hours
    FROM shifts WHERE program = 'vr' GROUP BY 1, 2
),
o AS (SELECT office, week_start, coalesce(c.valid_cards, 0) AS valid_cards, coalesce(c.duplicate_cards, 0) AS duplicate_cards,
             h.paid_hours
      FROM h LEFT JOIN c USING (office, week_start)),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', week_start, sum(valid_cards), sum(duplicate_cards), sum(paid_hours) FROM o GROUP BY week_start
)
SELECT office, week_start, valid_cards, duplicate_cards, paid_hours,
       round(valid_cards / nullif(paid_hours, 0), 2) AS cards_per_hour
FROM u;
CREATE VIEW v_vr_weekly AS SELECT * FROM all_vr_weekly WHERE office <> 'All offices';
CREATE VIEW v_vr_weekly_total AS SELECT * FROM all_vr_weekly WHERE office = 'All offices';

-- QC flags per office per week, with the rate per 100 GOTV shifts (v_qc_weekly_total: all offices).
CREATE VIEW all_qc_weekly AS
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
),
o AS (
    SELECT sh.office, sh.week_start, sh.shifts,
           coalesce(f.flags, 0) AS flags,
           coalesce(f.flash_knocking, 0) AS flash_knocking,
           coalesce(f.householding, 0) AS householding,
           coalesce(f.gaps, 0) AS gaps
    FROM sh LEFT JOIN f USING (office, week_start)
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', week_start, sum(shifts)::bigint, sum(flags)::bigint, sum(flash_knocking)::bigint,
           sum(householding)::bigint, sum(gaps)::bigint
    FROM o GROUP BY week_start
)
SELECT *, round(100.0 * flags / shifts, 1) AS flags_per_100_shifts FROM u;
CREATE VIEW v_qc_weekly AS SELECT * FROM all_qc_weekly WHERE office <> 'All offices';
CREATE VIEW v_qc_weekly_total AS SELECT * FROM all_qc_weekly WHERE office = 'All offices';

-- ---------- helper views for common questions ----------

-- Contact rate per office per week, Monday start (v_contact_rates_total: all offices).
CREATE VIEW all_contact_rates AS
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
CREATE VIEW v_contact_rates AS SELECT * FROM all_contact_rates WHERE office <> 'All offices';
CREATE VIEW v_contact_rates_total AS SELECT * FROM all_contact_rates WHERE office = 'All offices';

-- GOTV wages and cost per door to date (v_cost_per_door_total: all offices).
CREATE VIEW all_cost_per_door AS
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
CREATE VIEW v_cost_per_door AS SELECT * FROM all_cost_per_door WHERE office <> 'All offices';
CREATE VIEW v_cost_per_door_total AS SELECT * FROM all_cost_per_door WHERE office = 'All offices';

-- The weekly client report: doors, contacts, valid cards and paid hours per office per week
-- (v_weekly_report_total: the report's total row).
CREATE VIEW all_weekly_report AS
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
CREATE VIEW v_weekly_report AS SELECT * FROM all_weekly_report WHERE office <> 'All offices';
CREATE VIEW v_weekly_report_total AS SELECT * FROM all_weekly_report WHERE office = 'All offices';

-- One row per person with how much they have worked and whether they are active and regular.
-- The staff definitions (program plan) are GOTV definitions: registration canvassers get staff_type 'registration'
-- and are never counted as regulars or one-day hires.
CREATE VIEW v_canvasser_status AS
SELECT c.canvasser_id, c.full_name, c.office, c.program, c.role,
       count(DISTINCT s.shift_date) AS days_worked,
       min(s.shift_date) AS first_shift, max(s.shift_date) AS last_shift,
       max(s.shift_date) > (SELECT as_of_date FROM program_settings) - 7 AS active,
       CASE WHEN c.program <> 'gotv' THEN 'registration'
            WHEN count(DISTINCT s.shift_date) >= 5 THEN 'regular'
            WHEN count(DISTINCT s.shift_date) = 1 THEN 'one-day hire'
            ELSE 'occasional' END AS staff_type
FROM canvassers c JOIN shifts s USING (canvasser_id)
GROUP BY c.canvasser_id, c.full_name, c.office, c.program, c.role;

-- GOTV staff counts per office (v_gotv_staff_total: all offices), by the program plan's definitions: regular = 5 or
-- more days worked, one-day hire = exactly one day, active = a shift in the last 7 days. GOTV canvassers only.
CREATE VIEW all_gotv_staff AS
WITH o AS (
    SELECT office,
           count(*) AS gotv_canvassers,
           count(*) FILTER (WHERE active) AS active_canvassers,
           count(*) FILTER (WHERE active AND staff_type = 'regular') AS active_regulars,
           count(*) FILTER (WHERE active AND staff_type = 'occasional') AS active_occasional,
           count(*) FILTER (WHERE active AND staff_type = 'one-day hire') AS active_one_day_hires,
           count(*) FILTER (WHERE staff_type = 'regular') AS regulars_all_time,
           count(*) FILTER (WHERE staff_type = 'one-day hire') AS one_day_hires_all_time
    FROM v_canvasser_status WHERE program = 'gotv' GROUP BY office
)
SELECT * FROM o
UNION ALL
SELECT 'All offices', sum(gotv_canvassers)::bigint, sum(active_canvassers)::bigint, sum(active_regulars)::bigint,
       sum(active_occasional)::bigint, sum(active_one_day_hires)::bigint, sum(regulars_all_time)::bigint,
       sum(one_day_hires_all_time)::bigint
FROM o;
CREATE VIEW v_gotv_staff AS SELECT * FROM all_gotv_staff WHERE office <> 'All offices';
CREATE VIEW v_gotv_staff_total AS SELECT * FROM all_gotv_staff WHERE office = 'All offices';

-- Remaining turf per office by coverage band and density band (v_turf_summary_total: all offices, by band). Density
-- bands follow the program plan: dense = over 2,000 doors per square mile, sparse = under 1,000. For one number of
-- untouched doors across all turf, use doors_untouched in v_office_pace / v_office_pace_total.
CREATE VIEW all_turf_summary AS
WITH p AS (
    SELECT office, coverage,
           CASE WHEN doors_per_sq_mi > 2000 THEN 'dense' WHEN doors_per_sq_mi < 1000 THEN 'sparse' ELSE 'medium' END AS density,
           target_doors, doors_untouched, not_home_doors
    FROM v_precinct_coverage
),
o AS (
    SELECT office, coverage, density, count(*) AS precincts, sum(target_doors) AS target_doors,
           sum(doors_untouched) AS doors_untouched, sum(not_home_doors) AS not_home_doors
    FROM p GROUP BY 1, 2, 3
)
SELECT * FROM o
UNION ALL
SELECT 'All offices', coverage, density, sum(precincts)::bigint, sum(target_doors), sum(doors_untouched), sum(not_home_doors)
FROM o GROUP BY coverage, density;
CREATE VIEW v_turf_summary AS SELECT * FROM all_turf_summary WHERE office <> 'All offices';
CREATE VIEW v_turf_summary_total AS SELECT * FROM all_turf_summary WHERE office = 'All offices';

-- QC flags with the canvasser's name.
CREATE VIEW v_qc_flags_detail AS
SELECT f.flag_id, f.flag_date, date_trunc('week', f.flag_date)::date AS week_start, f.office, f.canvasser_id, c.full_name,
       f.shift_id, f.flag_type, f.status, f.evidence,
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

-- Registration QC call outcomes per office (v_qc_call_outcomes_total: all offices).
CREATE VIEW all_qc_call_outcomes AS
WITH o AS (
    SELECT v.office, q.outcome, count(*) AS calls FROM vr_qc_calls q JOIN vr_cards v USING (card_id) GROUP BY 1, 2
),
u AS (
    SELECT * FROM o
    UNION ALL
    SELECT 'All offices', outcome, sum(calls) FROM o GROUP BY outcome
)
SELECT office, outcome, calls, round(100.0 * calls / sum(calls) OVER (PARTITION BY office), 1) AS share_pct FROM u;
CREATE VIEW v_qc_call_outcomes AS SELECT * FROM all_qc_call_outcomes WHERE office <> 'All offices';
CREATE VIEW v_qc_call_outcomes_total AS SELECT * FROM all_qc_call_outcomes WHERE office = 'All offices';

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
-- The all_* views (office and total rows together) stay internal; the reader gets v_<name> and v_<name>_total.
DO $$
DECLARE v text;
BEGIN
    FOR v IN SELECT table_name FROM information_schema.views WHERE table_schema = 'program' AND table_name LIKE 'all\_%' LOOP
        EXECUTE format('REVOKE SELECT ON program.%I FROM pda_reader', v);
    END LOOP;
END
$$;
ALTER ROLE pda_reader SET search_path = program;
ALTER ROLE pda_reader SET default_transaction_read_only = on;
ALTER ROLE pda_reader SET statement_timeout = '5s';
