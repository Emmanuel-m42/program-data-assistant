"""Seeded generator for the fictional Riverbend Votes (GOTV) and Riverbend Registers (VR) programs.

Everything here is made up. The data is shaped so each demo question has a clear answer:
Eastgate is behind its door goal, Harbor slightly behind, Northside on pace; one Eastgate
canvasser has repeated householding flags; Oct 12 has a rolled-back flash-knocking shift that
widens the gap between the client's attempt count and our door count; a dense cluster of
untouched precincts sits southwest of every office; one Harbor registration canvasser has most
of the duplicate cards.

Run: uv run pda-generate  (writes data/csv/*.csv)
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 20261018
START = date(2026, 9, 21)  # Monday
AS_OF = date(2026, 10, 18)  # Sunday, last day of data
THIS_WEEK = date(2026, 10, 12)
LAST_WEEK = date(2026, 10, 5)
ELECTION_DAY = date(2026, 11, 3)
GOTV_LAST_KNOCK_DAY = date(2026, 11, 3)
VR_DEADLINE = date(2026, 10, 30)
OT_THRESHOLD = 40

OFFICES = {
    "Northside": dict(address="410 Grant Ave", lat=40.352, lon=-86.598, opened_on=date(2026, 9, 14)),
    "Eastgate": dict(address="88 Eastgate Plaza", lat=40.301, lon=-86.528, opened_on=date(2026, 9, 14)),
    "Harbor": dict(address="1200 Harbor Rd", lat=40.262, lon=-86.612, opened_on=date(2026, 9, 14)),
}

SITES = [
    ("S1", "Mill Street storefront", "215 Mill St", 40.238, -86.701, 2400),
    ("S2", "Westview Plaza suite", "9 Westview Plaza", 40.305, -86.672, 3100),
    ("S3", "Depot Road warehouse", "1630 Depot Rd", 40.252, -86.552, 1900),
    ("S4", "Canal Row office", "47 Canal Row", 40.268, -86.640, 2700),
]

FIRST = [
    "Avery", "Bianca", "Caleb", "Dana", "Elena", "Felix", "Gloria", "Hector", "Imani", "Jonah",
    "Kara", "Liam", "Maya", "Nadia", "Omar", "Paige", "Quinn", "Rosa", "Silas", "Tara",
    "Uriel", "Vera", "Wes", "Ximena", "Yusuf", "Zoe", "Aldo", "Brynn", "Cyrus", "Delia",
    "Emmett", "Farah", "Gideon", "Hana", "Ivo", "Jade", "Kofi", "Lena", "Milo", "Noor",
    "Otis", "Petra", "Rafael", "Sage", "Theo", "Uma", "Viktor", "Willa", "Yara", "Zane",
]
LAST = [
    "Abbott", "Barros", "Castellano", "Dunmore", "Ekwueme", "Farrow", "Galloway", "Hollis",
    "Ibarra", "Jessup", "Kowalczyk", "Lattimore", "Moreau", "Nkemelu", "Okafor", "Pemberton",
    "Quarles", "Rasmussen", "Sandoval", "Thibodeaux", "Underhill", "Vasquez", "Whitlock",
    "Yamada", "Zielinski", "Ashby", "Brandt", "Corwin", "Delgado", "Eastman", "Fairbanks",
    "Grisham", "Haddad", "Iverson", "Juarez", "Kincaid", "Lindgren", "Marsh", "Novak",
]

# Named people the stories hang on (all fictional).
STORY = {
    "dorian": ("Dorian Pratt", "Eastgate", "gotv", "canvasser"),
    "jalen": ("Jalen Ortiz", "Eastgate", "gotv", "canvasser"),
    "tomas": ("Tomas Reyes", "Northside", "gotv", "canvasser"),
    "priya": ("Priya Nandakumar", "Harbor", "gotv", "canvasser"),
    "andre": ("Andre Whitfield", "Eastgate", "gotv", "canvasser"),
    "ellis": ("Ellis Warren", "Northside", "gotv", "field lead"),
    "sofia": ("Sofia Lindqvist", "Eastgate", "gotv", "canvasser"),
    "marcus": ("Marcus Bell", "Harbor", "vr", "registration canvasser"),
    "renata": ("Renata Cole", "Harbor", "vr", "registration canvasser"),
    "fixA": ("Leon Mbeki", "Harbor", "gotv", "canvasser"),
    "fixB": ("Carmen Ruiz", "Northside", "vr", "registration canvasser"),
    "fixC": ("Hugo Brennan", "Eastgate", "gotv", "canvasser"),
}

PAY_RATES = {"canvasser": 20.00, "field lead": 24.00, "registration canvasser": 19.00, "registration lead": 23.00}

# GOTV levers per office.
DOORS_PER_HOUR = {"Northside": 13.0, "Eastgate": 10.5, "Harbor": 12.0}
SHIFT_RAMP = {"Northside": (6, 11), "Eastgate": (5, 8), "Harbor": (6, 10)}
CONTACT_P = {  # by week index 0..3
    "Northside": [0.27, 0.27, 0.26, 0.30],
    "Eastgate": [0.26, 0.27, 0.27, 0.23],
    "Harbor": [0.25, 0.25, 0.25, 0.27],
}
GOAL_RATIO = {"Northside": 1.04, "Eastgate": 0.82, "Harbor": 0.95}  # projected / goal
VR_CPH = {"Northside": 3.2, "Eastgate": 2.4, "Harbor": 2.7}
VR_REQUIRED_CPH = 2.95

# Weekly QC flag plan for weeks 1-3 (week 4 is hand-written in the story).
QC_EARLY = [{"Northside": 3, "Eastgate": 2, "Harbor": 6}, {"Northside": 2, "Eastgate": 3, "Harbor": 5},
            {"Northside": 2, "Eastgate": 2, "Harbor": 4}]

PROGRAM_DAYS = [START + timedelta(days=i) for i in range((AS_OF - START).days + 1)]


def week_index(d: date) -> int:
    return (d - START).days // 7


def km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def offset(lat, lon, dist_km, bearing_deg):
    b = math.radians(bearing_deg)
    return (lat + dist_km * math.cos(b) / 111.0, lon + dist_km * math.sin(b) / (111.0 * math.cos(math.radians(lat))))


@dataclass
class Person:
    canvasser_id: str
    full_name: str
    office: str
    program: str
    role: str
    start_date: date
    one_day: bool = False
    reliability: float = 0.6
    days: set = field(default_factory=set)


@dataclass
class Shift:
    shift_id: str
    program: str
    shift_date: date
    person: Person
    office: str
    clock_in: datetime
    clock_out: datetime | None
    approval_status: str = "approved"
    fix_note: str = ""
    story: str = ""

    @property
    def paid_hours(self):
        if self.clock_out is None:
            return None
        return round((self.clock_out - self.clock_in).total_seconds() / 3600, 2)


class Gen:
    def __init__(self, seed=SEED):
        self.r = random.Random(seed)
        self.used_names: set[str] = set()
        self.people: list[Person] = []
        self.shifts: list[Shift] = []
        self.knocks: list[dict] = []
        self.flags: list[dict] = []
        self.cards: list[dict] = []
        self.calls: list[dict] = []
        self.precincts: list[dict] = []

    # ---------- people ----------
    def name(self):
        while True:
            n = f"{self.r.choice(FIRST)} {self.r.choice(LAST)}"
            if n not in self.used_names:
                self.used_names.add(n)
                return n

    def make_people(self):
        n = 0
        story_people = {}
        for key, (full, office, program, role) in STORY.items():
            n += 1
            self.used_names.add(full)
            p = Person(f"C{n:03d}", full, office, program, role, START, reliability=0.0)
            story_people[key] = p
            self.people.append(p)
        self.story = story_people
        pools = {("gotv", "Northside"): 33, ("gotv", "Eastgate"): 26, ("gotv", "Harbor"): 31,
                 ("vr", "Northside"): 9, ("vr", "Eastgate"): 9, ("vr", "Harbor"): 8}
        for (program, office), size in pools.items():
            for i in range(size):
                n += 1
                if program == "gotv":
                    role = "field lead" if i < 2 else "canvasser"
                else:
                    role = "registration lead" if i < 1 else "registration canvasser"
                start = START if self.r.random() < 0.5 or i < 2 else START + timedelta(days=self.r.randint(1, 23))
                one_day = role in ("canvasser", "registration canvasser") and self.r.random() < 0.16
                rel = 0.0 if one_day else (self.r.uniform(0.55, 0.85) if self.r.random() < 0.65 else self.r.uniform(0.15, 0.35))
                self.people.append(Person(f"C{n:03d}", self.name(), office, program, role, start, one_day, rel))
        # Story people work regularly but are scheduled by hand in the story weeks.
        for key in ("dorian", "jalen", "tomas", "priya", "andre", "fixA", "fixC"):
            story_people[key].reliability = 0.6
        for key in ("renata", "fixB"):
            story_people[key].reliability = 0.65
        story_people["ellis"].reliability = 0.8
        story_people["sofia"].reliability = 0.7
        story_people["marcus"].reliability = 0.7

    # ---------- shifts ----------
    def add_shift(self, program, d, person, hours, start_hour=None, **kw):
        if start_hour is None:
            start_hour = self.r.choice([9.5, 10, 10.5, 15, 15.5, 16]) if hours <= 5.5 else self.r.choice([9, 9.5])
        cin = datetime.combine(d, datetime.min.time()) + timedelta(hours=start_hour, minutes=self.r.randint(-6, 8))
        cout = cin + timedelta(hours=hours, minutes=self.r.randint(-5, 5))
        s = Shift(f"{'G' if program == 'gotv' else 'R'}{len(self.shifts) + 1:05d}", program, d, person, person.office, cin, cout, **kw)
        person.days.add(d)
        self.shifts.append(s)
        return s

    def schedule(self):
        st = self.story
        # Hand-scheduled story weeks. Long shifts for the overtime stories.
        forced: dict[tuple[str, date], float] = {}
        week4 = [THIS_WEEK + timedelta(days=i) for i in range(7)]
        for i, d in enumerate(week4):
            if i < 6:
                forced[(st["ellis"].canvasser_id, d)] = 7.5
                forced[(st["marcus"].canvasser_id, d)] = 7.0
            if i in (0, 1, 2, 4, 5):
                forced[(st["sofia"].canvasser_id, d)] = 8.5
        for d in (date(2026, 10, 13), date(2026, 10, 15), date(2026, 10, 17), date(2026, 10, 18)):
            forced[(st["dorian"].canvasser_id, d)] = 4.5
        forced[(st["jalen"].canvasser_id, date(2026, 10, 12))] = 4.5
        forced[(st["tomas"].canvasser_id, date(2026, 10, 14))] = 4.5
        forced[(st["priya"].canvasser_id, date(2026, 10, 18))] = 4.5
        forced[(st["andre"].canvasser_id, date(2026, 10, 17))] = 5.0
        forced[(st["fixA"].canvasser_id, date(2026, 10, 16))] = 4.5
        forced[(st["fixB"].canvasser_id, date(2026, 10, 17))] = 5.0
        forced[(st["fixC"].canvasser_id, date(2026, 10, 15))] = 4.5
        story_ids = {p.canvasser_id for p in st.values()}

        for d in PROGRAM_DAYS:
            w = week_index(d)
            for program in ("gotv", "vr"):
                for office in OFFICES:
                    if program == "gotv":
                        lo, hi = SHIFT_RAMP[office]
                        target = lo + (hi - lo) * (d - START).days / (len(PROGRAM_DAYS) - 1)
                        target = round(target + (1.5 if d.weekday() >= 5 else 0) + self.r.uniform(-1, 1))
                    else:
                        target = self.r.choice([3, 4, 4]) + (1 if d.weekday() >= 5 else 0)
                    pool = [p for p in self.people if p.program == program and p.office == office and p.start_date <= d]
                    chosen = []
                    for p in pool:
                        key = (p.canvasser_id, d)
                        if key in forced:
                            chosen.append((p, forced[key]))
                    for p in pool:
                        if (p.canvasser_id, d) in forced:
                            continue
                        if p.canvasser_id in story_ids and w == 3:
                            continue  # story people only work their forced shifts in week 4
                        if p.one_day:
                            if not p.days and p.start_date == d:
                                chosen.append((p, round(self.r.uniform(3.5, 4.5), 1)))
                            continue
                    others = [p for p in pool if not p.one_day and (p.canvasser_id, d) not in forced
                              and not (p.canvasser_id in story_ids and w == 3)]
                    self.r.shuffle(others)
                    others.sort(key=lambda p: -(p.reliability + self.r.uniform(-0.3, 0.3)))
                    for p in others:
                        if len(chosen) >= target:
                            break
                        if self.r.random() < p.reliability + 0.15:
                            chosen.append((p, round(self.r.uniform(3.5, 5.0), 1)))
                    for p, hours in chosen:
                        self.add_shift(program, d, p, hours)

        # Approval status for this week's payroll stories.
        for s in self.shifts:
            if s.person is st["fixA"] and s.shift_date == date(2026, 10, 16):
                s.clock_out, s.approval_status, s.fix_note = None, "needs_fix", "missing clock out"
            if s.person is st["fixB"] and s.shift_date == date(2026, 10, 17):
                s.clock_out, s.approval_status, s.fix_note = None, "needs_fix", "missing clock out"
            if s.person is st["fixC"] and s.shift_date == date(2026, 10, 15):
                s.approval_status, s.fix_note = "needs_fix", "clocked in under Harbor, worked Eastgate turf"
        for key in ("ellis", "sofia", "marcus"):
            total = 0.0
            for s in sorted((s for s in self.shifts if s.person is st[key] and s.shift_date >= THIS_WEEK), key=lambda s: s.shift_date):
                total += s.paid_hours or 0
                if total > OT_THRESHOLD:
                    s.approval_status, s.fix_note = "pending", "overtime needs field director approval"

    # ---------- knocks ----------
    def knock_times(self, s: Shift, n: int):
        start = s.clock_in + timedelta(minutes=self.r.randint(8, 15))
        end = (s.clock_out or s.clock_in + timedelta(hours=4.5)) - timedelta(minutes=self.r.randint(5, 12))
        span = (end - start).total_seconds()
        gaps = [self.r.gammavariate(2.0, 1.0) for _ in range(n)]
        scale = span / sum(gaps)
        t, out = start, []
        for g in gaps:
            t = t + timedelta(seconds=g * scale)
            out.append(t)
        return out

    def result(self, office, d):
        cp = CONTACT_P[office][week_index(d)]
        x = self.r.random()
        if x < cp:
            return "canvassed", self.r.choices(["supporter", "leaning", "undecided", "opposed"], [45, 20, 25, 10])[0]
        if x < cp + 0.08:
            return "refused", ""
        if x < cp + 0.11:
            return "inaccessible", ""
        return "not home", ""

    def make_knocks(self):
        """Knock times, results and patterns first; addresses are assigned after turf is sized."""
        st = self.story
        early_flag_shifts = self.pick_early_flags()
        for s in sorted((s for s in self.shifts if s.program == "gotv"), key=lambda s: s.clock_in):
            hours = s.paid_hours or 4.5
            n = max(8, round(hours * DOORS_PER_HOUR[s.office] * self.r.uniform(0.85, 1.15)))
            times = self.knock_times(s, n)
            rows = []
            for t in times:
                res, ans = self.result(s.office, s.shift_date)
                rows.append(dict(shift=s, t=t, result=res, survey=ans, kind="first", rolled_back=False))
            plan = early_flag_shifts.get(s.shift_id)
            if s.person is st["jalen"] and s.shift_date == date(2026, 10, 12):
                plan = "flash_full"
            elif s.person is st["dorian"] and s.shift_date in (date(2026, 10, 13), date(2026, 10, 17), date(2026, 10, 18)):
                plan = "householding"
            elif s.person is st["tomas"] and s.shift_date == date(2026, 10, 14):
                plan = "householding"
            elif s.person is st["priya"] and s.shift_date == date(2026, 10, 18):
                plan = "flash"
            elif s.person is st["andre"] and s.shift_date == date(2026, 10, 17):
                plan = "gap"
            if plan:
                rows = self.inject(s, rows, plan)
            # Repeat attempts: some not-home doors get a second knock later in the shift,
            # some knocks are second passes on doors that were not home on an earlier day.
            for i, k in enumerate(rows):
                if k["kind"] == "first" and k["result"] == "not home" and self.r.random() < 0.06 and i + 5 < len(rows):
                    j = self.r.randint(i + 3, len(rows) - 1)
                    if rows[j]["kind"] == "first":
                        rows[j]["kind"] = ("same_day", i)
                elif k["kind"] == "first" and self.r.random() < 0.07 and s.shift_date > START + timedelta(days=4):
                    k["kind"] = "second_pass"
            self.knocks.extend(rows)

    def pick_early_flags(self):
        plans = {}
        for w, per_office in enumerate(QC_EARLY):
            days = [START + timedelta(days=7 * w + i) for i in range(7)]
            for office, count in per_office.items():
                cands = [s for s in self.shifts if s.program == "gotv" and s.office == office and s.shift_date in days
                         and s.person.canvasser_id not in {p.canvasser_id for p in self.story.values()}
                         and s.shift_id not in plans]
                for s in self.r.sample(cands, count):
                    plans[s.shift_id] = self.r.choices(["flash", "householding", "gap"], [3, 4, 3])[0]
        return plans

    def inject(self, s, rows, plan):
        if plan == "flash_full":
            # Whole shift recorded in about 40 minutes: every knock is rolled back.
            t0 = s.clock_in + timedelta(minutes=50)
            n = 142
            rows = []
            t = t0
            for _ in range(n):
                t = t + timedelta(seconds=self.r.randint(10, 22))
                res = "not home" if self.r.random() < 0.8 else "canvassed"
                rows.append(dict(shift=s, t=t, result=res, survey="supporter" if res == "canvassed" else "", kind="first", rolled_back=True))
            self.add_flag(s, "flash_knocking", rows, rolled_back=True,
                          evidence=f"{n} knocks recorded between {rows[0]['t']:%H:%M:%S} and {rows[-1]['t']:%H:%M:%S}, median {self.median_gap(rows)} s apart; whole shift rolled back")
            return rows
        if plan == "flash":
            i = self.r.randint(5, max(6, len(rows) - 20))
            t = rows[i]["t"]
            run = []
            for k in rows[i:i + 13]:
                t = t + timedelta(seconds=self.r.randint(8, 16))
                k["t"], k["result"], k["survey"] = t, "not home", ""
                run.append(k)
            for k in rows[i + 13:]:
                if k["t"] <= t:
                    k["t"] = t + timedelta(seconds=self.r.randint(60, 200))
                    t = k["t"]
            open_flag = s.shift_date >= date(2026, 10, 17)
            for k in run:
                k["rolled_back"] = not open_flag
            self.add_flag(s, "flash_knocking", run, rolled_back=not open_flag,
                          evidence=f"{len(run)} consecutive knocks between {run[0]['t']:%H:%M:%S} and {run[-1]['t']:%H:%M:%S}, median {self.median_gap(run)} s apart")
            return rows
        if plan == "householding":
            i = self.r.randint(5, max(6, len(rows) - 12))
            run = rows[i:i + 6]
            t = run[0]["t"]
            ans = self.r.choice(["supporter", "undecided"])
            for k in run:
                t = t + timedelta(seconds=self.r.randint(20, 35))
                k["t"], k["result"], k["survey"], k["kind"] = t, "canvassed", ans, "household"
            for k in rows[i + 6:]:
                if k["t"] <= t:
                    k["t"] = t + timedelta(seconds=self.r.randint(60, 200))
                    t = k["t"]
            self.add_flag(s, "householding", run, rolled_back=False, evidence=None)
            return rows
        if plan == "gap":
            mid = s.clock_in + (s.clock_out - s.clock_in) / 2
            g0, g1 = mid - timedelta(minutes=40), mid + timedelta(minutes=42)
            kept = [k for k in rows if not (g0 <= k["t"] <= g1)]
            before = max(k["t"] for k in kept if k["t"] < g0)
            after = min(k["t"] for k in kept if k["t"] > g1)
            mins = round((after - before).total_seconds() / 60)
            self.add_flag(s, "gap", [], rolled_back=False,
                          evidence=f"no knocks for {mins} minutes, last knock {before:%H:%M:%S}, next knock {after:%H:%M:%S}, while clocked in",
                          window=(before, after))
            return kept
        raise ValueError(plan)

    @staticmethod
    def median_gap(run):
        g = sorted((b["t"] - a["t"]).total_seconds() for a, b in zip(run, run[1:]))
        return round(g[len(g) // 2])

    def add_flag(self, s, ftype, run, rolled_back, evidence, window=None):
        status = "open" if s.shift_date >= date(2026, 10, 17) else "reviewed"
        f = dict(flag_id=f"QC{len(self.flags) + 1:03d}", shift=s, flag_type=ftype, run=run, evidence=evidence,
                 window=window, status=status, rolled_back=rolled_back)
        self.flags.append(f)

    # ---------- turf ----------
    def make_turf(self):
        """Size each office's precincts from the first-pass knocks it needs, then assign doors."""
        r = self.r
        pid = 0
        first_need = {o: sum(1 for k in self.knocks if k["shift"].office == o and k["kind"] == "first") for o in OFFICES}
        bearings = {"Northside": (-60, 120), "Eastgate": (-30, 170), "Harbor": (60, 200)}
        for office, o in OFFICES.items():
            near_n, out_n = 10, 2
            outskirts = []
            for j in range(out_n):
                b = r.uniform(*bearings[office])
                lat, lon = offset(o["lat"], o["lon"], r.uniform(5.5, 7.0), b)
                dens = r.randint(260, 620)
                outskirts.append(dict(lat=lat, lon=lon, dens=dens, size=r.randint(650, 900)))
            out_total = sum(p["size"] for p in outskirts)
            near_sum = first_need[office] - int(0.35 * out_total)
            weights = [r.uniform(0.7, 1.3) for _ in range(near_n)]
            near = []
            for j, wt in enumerate(weights):
                b = r.uniform(*bearings[office])
                lat, lon = offset(o["lat"], o["lon"], 0.5 + 3.6 * (j / near_n) + r.uniform(0, 0.4), b)
                near.append(dict(lat=lat, lon=lon, dens=r.randint(1400, 3000), size=int(near_sum * wt / sum(weights))))
            for p in near + outskirts:
                pid += 1
                self.precincts.append(dict(precinct_id=f"P{pid:02d}", office=office, **p))
        # Dense cluster southwest of everything, on Harbor's turf, never reached.
        for j, (dlat, dlon) in enumerate([(0.0, 0.0), (0.012, 0.016), (-0.011, 0.012), (0.004, -0.017)]):
            pid += 1
            self.precincts.append(dict(precinct_id=f"P{pid:02d}", office="Harbor", lat=40.236 + dlat, lon=-86.703 + dlon,
                                       dens=r.randint(3300, 4300), size=r.randint(1550, 1950), cluster=True))
        for p in self.precincts:
            p["area"] = round(p["size"] / p["dens"], 3)
            p["dist"] = km(p["lat"], p["lon"], OFFICES[p["office"]]["lat"], OFFICES[p["office"]]["lon"])
            p["doors"] = self.make_doors(p)
        self.assign_addresses()

    def make_doors(self, p):
        doors, b = [], 0
        apt_share = 0.35 if p["dens"] > 1200 else 0.05
        while len(doors) < p["size"]:
            b += 1
            addr = f"{p['precinct_id']}-{b:04d}"
            if self.r.random() < apt_share:
                units = self.r.randint(4, 12)
                for u in range(1, units + 1):
                    doors.append((addr, f"{(u - 1) // 4 + 1}{'ABCD'[(u - 1) % 4]}"))
            else:
                doors.append((addr, ""))
        return doors[: p["size"]]

    def assign_addresses(self):
        for office in OFFICES:
            precs = sorted([p for p in self.precincts if p["office"] == office and not p.get("cluster")],
                           key=lambda p: (p["dens"] < 1000, p["dist"]))
            queue = [(p, d) for p in precs for d in p["doors"]]
            qi = 0
            not_home_pool: list[tuple] = []
            knocks = sorted((k for k in self.knocks if k["shift"].office == office), key=lambda k: k["t"])
            by_shift: dict[str, list] = {}
            for k in knocks:
                by_shift.setdefault(k["shift"].shift_id, []).append(k)
            for k in knocks:
                kind = k["kind"]
                if isinstance(kind, tuple):  # same-day repeat of an earlier knock in the shift
                    src = by_shift[k["shift"].shift_id][kind[1]]
                    if "door" in src and src["t"] < k["t"]:
                        k["prec"], k["door"] = src["prec"], src["door"]
                        continue
                    kind = "first"
                if kind == "second_pass" and len(not_home_pool) > 50:
                    prec, door = not_home_pool.pop(self.r.randrange(len(not_home_pool) - 30))
                    k["prec"], k["door"] = prec, door
                    if k["result"] == "not home":
                        not_home_pool.append((prec, door))
                    continue
                k["prec"], k["door"] = queue[qi]
                qi += 1
                if k["result"] == "not home" and not k["rolled_back"]:
                    not_home_pool.append((k["prec"], k["door"]))
        # A householding run is one building: move the whole run onto an apartment building in its precinct.
        for f in self.flags:
            if f["flag_type"] == "householding":
                run = f["run"]
                prec = run[0]["prec"]
                buildings: dict[str, list] = {}
                for d in prec["doors"]:
                    if d[1]:
                        buildings.setdefault(d[0], []).append(d)
                big = [b for b in buildings.values() if len(b) >= len(run)]
                if big:
                    units = self.r.choice(big)[: len(run)]
                else:
                    units = [(run[0]["door"][0], f"{u}A") for u in range(1, len(run) + 1)]
                addr = units[0][0]
                for k, door in zip(run, units):
                    k["prec"], k["door"] = prec, door
                f["evidence"] = (f"{len(run)} canvassed results at {addr} (units {', '.join(d[1] or '-' for d in units[:len(run)])}) "
                                 f"between {run[0]['t']:%H:%M:%S} and {run[-1]['t']:%H:%M:%S}, all answered '{run[0]['survey']}'")

    # ---------- registration drive ----------
    def make_vr(self):
        st = self.story
        regs = []
        for s in sorted((s for s in self.shifts if s.program == "vr"), key=lambda s: s.clock_in):
            hours = s.paid_hours or 5.0
            cph = VR_CPH[s.office] * self.r.uniform(0.8, 1.2)
            dup_p = 0.30 if s.person is st["renata"] else 0.02
            n = max(1, round(hours * cph / (1 - dup_p)))
            t0 = s.clock_in + timedelta(minutes=10)
            for i in range(n):
                t = t0 + timedelta(seconds=self.r.uniform(0, (hours - 0.3) * 3600))
                dup_of = None
                if regs and self.r.random() < dup_p:
                    pool = [c for c in regs[-400:] if c["office"] == s.office and c["duplicate_of"] is None]
                    if pool:
                        dup_of = self.r.choice(pool)
                card_id = f"VR{len(regs) + 1:05d}"
                regs.append(dict(card_id=card_id, shift_id=s.shift_id, canvasser_id=s.person.canvasser_id, office=s.office,
                                 collected_at=t, registrant_name=dup_of["registrant_name"] if dup_of else f"{self.r.choice(FIRST)} {self.r.choice(LAST)}",
                                 duplicate_of=dup_of["card_id"] if dup_of else None, t=t))
        regs.sort(key=lambda c: c["collected_at"])
        groups = {}
        for c in regs:
            root = c["duplicate_of"]
            if root:
                groups.setdefault(root, f"DG{len(groups) + 1:03d}")
        for c in regs:
            gid = groups.get(c["card_id"]) or (groups.get(c["duplicate_of"]) if c["duplicate_of"] else None)
            c["duplicate_group"] = gid or ""
            c["is_duplicate"] = c["duplicate_of"] is not None
        self.cards = regs
        n = 0
        for c in regs:
            if c["is_duplicate"] or c["collected_at"].date() > AS_OF - timedelta(days=2):
                continue
            if self.r.random() < 0.4:
                n += 1
                outcome = self.r.choices(["confirmed", "unreachable", "wrong_info"], [72, 21, 7])[0]
                called = c["collected_at"] + timedelta(days=self.r.randint(1, 2), hours=self.r.randint(1, 6))
                self.calls.append(dict(call_id=f"QCC{n:04d}", card_id=c["card_id"], called_at=called, outcome=outcome))

    # ---------- goals ----------
    def goals(self):
        all_days = [START + timedelta(days=i) for i in range((GOTV_LAST_KNOCK_DAY - START).days + 1)]
        left = (GOTV_LAST_KNOCK_DAY - AS_OF).days
        rows = []
        for office in OFFICES:
            daily: dict[date, set] = {}
            for k in self.knocks:
                if k["shift"].office == office and not k["rolled_back"]:
                    daily.setdefault(k["t"].date(), set()).add(k["door"])
            doors = sum(len(v) for v in daily.values())
            last7 = sum(len(v) for d, v in daily.items() if d > AS_OF - timedelta(days=7))
            projected = doors + last7 / 7 * left
            goal_total = projected / GOAL_RATIO[office]
            shape = [0.6 + 0.9 * i / (len(all_days) - 1) for i in range(len(all_days))]
            scale = goal_total / sum(shape)
            acc = 0
            for i, d in enumerate(all_days):
                g = round(shape[i] * scale)
                rows.append(dict(goal_date=d, office=office, door_goal=g))
                acc += g
        self.daily_goals = rows
        vr = []
        days_left = (VR_DEADLINE - AS_OF).days
        valid_total = sum(1 for c in self.cards if not c["is_duplicate"])
        hours7 = sum((s.paid_hours or 0) for s in self.shifts if s.program == "vr" and s.shift_date > AS_OF - timedelta(days=7)) / 7
        goal_total = valid_total + VR_REQUIRED_CPH * hours7 * days_left
        share = {o: sum(1 for c in self.cards if c["office"] == o and not c["is_duplicate"]) for o in OFFICES}
        for o in OFFICES:
            vr.append(dict(office=o, card_goal=int(round(goal_total * share[o] / valid_total / 10) * 10)))
        self.vr_goals = vr

    # ---------- output ----------
    def write(self, out: Path):
        out.mkdir(parents=True, exist_ok=True)

        def w(name, header, rows):
            with open(out / f"{name}.csv", "w", newline="") as fh:
                cw = csv.writer(fh)
                cw.writerow(header)
                cw.writerows(rows)

        w("program_settings", ["as_of_date", "this_week_start", "last_week_start", "election_day", "gotv_last_knock_day",
                               "vr_deadline", "overtime_threshold_hours"],
          [[AS_OF, THIS_WEEK, LAST_WEEK, ELECTION_DAY, GOTV_LAST_KNOCK_DAY, VR_DEADLINE, OT_THRESHOLD]])
        w("offices", ["office", "address", "lat", "lon", "opened_on"],
          [[n, o["address"], o["lat"], o["lon"], o["opened_on"]] for n, o in OFFICES.items()])
        w("pay_rates", ["role", "hourly_rate"], [[k, f"{v:.2f}"] for k, v in PAY_RATES.items()])
        w("canvassers", ["canvasser_id", "full_name", "office", "program", "role", "start_date", "days_worked"],
          [[p.canvasser_id, p.full_name, p.office, p.program, p.role, min(p.days) if p.days else p.start_date, len(p.days)]
           for p in self.people if p.days])
        w("shifts", ["shift_id", "program", "shift_date", "canvasser_id", "office", "clock_in", "clock_out", "paid_hours",
                     "approval_status", "fix_note"],
          [[s.shift_id, s.program, s.shift_date, s.person.canvasser_id, s.office, f"{s.clock_in:%Y-%m-%d %H:%M:%S}",
            f"{s.clock_out:%Y-%m-%d %H:%M:%S}" if s.clock_out else "", "" if s.paid_hours is None else s.paid_hours,
            s.approval_status, s.fix_note] for s in sorted(self.shifts, key=lambda s: s.shift_id)])
        w("precincts", ["precinct_id", "name", "office", "lat", "lon", "area_sq_mi", "target_doors", "doors_per_sq_mi"],
          [[p["precinct_id"], f"Precinct {p['precinct_id'][1:]}", p["office"], round(p["lat"], 5), round(p["lon"], 5),
            p["area"], p["size"], p["dens"]] for p in self.precincts])
        knocks = sorted(self.knocks, key=lambda k: k["t"])
        rows = []
        for i, k in enumerate(knocks, 1):
            addr, unit = k["door"]
            rows.append([f"K{i:06d}", k["shift"].shift_id, k["shift"].person.canvasser_id, k["shift"].office,
                         k["prec"]["precinct_id"], f"{k['t']:%Y-%m-%d %H:%M:%S}", addr, unit,
                         f"{addr}-{unit}" if unit else addr, k["result"], k["survey"], "true" if k["rolled_back"] else "false"])
        w("knocks", ["knock_id", "shift_id", "canvasser_id", "office", "precinct_id", "knocked_at", "address_id", "unit",
                     "door_id", "result", "survey_answer", "rolled_back"], rows)
        w("daily_goals", ["goal_date", "office", "door_goal"], [[g["goal_date"], g["office"], g["door_goal"]] for g in self.daily_goals])
        # Client report pulls every attempt at end of day, before QC rollbacks.
        rep: dict[tuple, list] = {}
        for k in knocks:
            key = (k["t"].date(), k["shift"].office)
            rep.setdefault(key, [0, 0])
            rep[key][0] += 1
            rep[key][1] += k["result"] == "canvassed"
        w("client_daily_report", ["report_date", "office", "doors_reported", "contacts_reported"],
          [[d, o, v[0], v[1]] for (d, o), v in sorted(rep.items())])
        w("qc_flags", ["flag_id", "shift_id", "canvasser_id", "office", "flag_date", "flag_type", "evidence", "evidence_start",
                       "evidence_end", "knock_count", "status", "knocks_rolled_back"],
          [[f["flag_id"], f["shift"].shift_id, f["shift"].person.canvasser_id, f["shift"].office, f["shift"].shift_date,
            f["flag_type"], f["evidence"],
            f"{(f['run'][0]['t'] if f['run'] else f['window'][0]):%Y-%m-%d %H:%M:%S}",
            f"{(f['run'][-1]['t'] if f['run'] else f['window'][1]):%Y-%m-%d %H:%M:%S}",
            len(f["run"]), f["status"], "true" if f["rolled_back"] else "false"] for f in self.flags])
        w("candidate_office_sites", ["site_id", "name", "address", "lat", "lon", "monthly_rent"], [list(s) for s in SITES])
        w("vr_goals", ["office", "card_goal"], [[g["office"], g["card_goal"]] for g in self.vr_goals])
        w("vr_cards", ["card_id", "shift_id", "canvasser_id", "office", "collected_at", "registrant_name", "duplicate_group_id",
                       "is_duplicate"],
          [[c["card_id"], c["shift_id"], c["canvasser_id"], c["office"], f"{c['collected_at']:%Y-%m-%d %H:%M:%S}",
            c["registrant_name"], c["duplicate_group"], "true" if c["is_duplicate"] else "false"] for c in self.cards])
        w("vr_qc_calls", ["call_id", "card_id", "called_at", "outcome"],
          [[c["call_id"], c["card_id"], f"{c['called_at']:%Y-%m-%d %H:%M:%S}", c["outcome"]] for c in self.calls])


def generate(out: Path) -> None:
    g = Gen()
    g.make_people()
    g.schedule()
    g.make_knocks()
    g.make_turf()
    g.make_vr()
    g.goals()
    g.write(out)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Generate the fictional program data as CSV files.")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "data" / "csv"))
    args = ap.parse_args()
    generate(Path(args.out))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
