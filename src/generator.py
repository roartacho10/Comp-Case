"""Synthetic world generator.

Generation follows the causal order of the world:
1. skeleton (country, area, level, teams, managers)
2. hidden cause of risk
3. active signals, drawn from the cause (at the level where each signal exists: person or team)
4. raw data built to exhibit exactly those signals
5. event history consistent with the raw data
6. the Comp network: closed cases from other companies, under the same rules

Every number comes from the assumptions base. Same assumptions + same seed = same data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.names import random_name
from src.signals import DAYS_PER_MONTH, DAYS_PER_YEAR, milestone_active, milestones

CAUSES = ["remuneração", "crescimento", "gestor"]
NO_CAUSE, EXTERNAL = "nenhuma", "externa"
IC, TEAM_MANAGER, LEADER = "Individual", "Gestor de time", "Liderança"
MANAGER_LEVEL = "Gestor"

CONTEXT_TEMPLATES = {
    "proposta_externa": [
        "Na conversa de carreira, comentou que tem recebido abordagens de recrutadores com propostas acima do salário atual.",
        "Mencionou ter participado de processos seletivos fora da empresa e que as faixas oferecidas eram maiores.",
    ],
    "fim_de_projeto_sem_escopo": [
        "Ata de encerramento do projeto {project}: entregas concluídas; {name} ainda sem novo escopo definido.",
        "Projeto {project} encerrado. Próximos passos de {name} a definir.",
    ],
    "pedido_crescimento_sem_plano": [
        "Na conversa de carreira, disse que quer assumir mais responsabilidade e liderar iniciativas; não há plano de desenvolvimento registrado.",
        "Pediu para discutir próximos passos de carreira; o plano de desenvolvimento ainda não foi formalizado.",
    ],
    "neutro": [
        "Conversa de carreira: satisfação com o escopo atual e interesse em aprofundar a área técnica.",
        "Ata de projeto: andamento conforme o planejado.",
        "Conversa de carreira: sem pedidos ou preocupações registradas.",
    ],
}
PROJECTS = ["Atlas", "Orion", "Pulsar", "Aurora", "Kepler", "Vega", "Lyra", "Nimbus"]


@dataclass
class World:
    public: dict[str, pd.DataFrame] = field(default_factory=dict)
    hidden: dict[str, pd.DataFrame] = field(default_factory=dict)
    notes: dict[str, float] = field(default_factory=dict)


def _exact_labels(dist: dict[str, float], n: int, rng) -> np.ndarray:
    """Labels in exact proportions (largest remainder), shuffled."""
    raw = {k: v * n for k, v in dist.items()}
    counts = {k: int(np.floor(v)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - counts[k], reverse=True)[: n - sum(counts.values())]:
        counts[k] += 1
    labels = np.array([k for k, c in counts.items() for _ in range(c)], dtype=object)
    rng.shuffle(labels)
    return labels


def _allocate(weights: dict[str, float], n: int) -> dict[str, int]:
    raw = {k: v / sum(weights.values()) * n for k, v in weights.items()}
    counts = {k: int(np.floor(v)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - counts[k], reverse=True)[: n - sum(counts.values())]:
        counts[k] += 1
    return counts


def _trunc_normal(rng, mean, sd, lo, hi) -> float:
    for _ in range(200):
        x = rng.normal(mean, sd)
        if lo <= x <= hi:
            return float(x)
    return float(rng.uniform(lo, hi))


def _days_ago(t0: pd.Timestamp, days: float) -> pd.Timestamp:
    return (t0 - pd.Timedelta(days=int(round(days)))).normalize()


def generate_world(a: Assumptions) -> World:
    rng = np.random.default_rng(a.int("general.seed"))
    t0 = a.date("general.reference_date")
    n = a.int("general.n_employees")
    signals = a.signals
    p_with, p_without = a.num("signals.prob_with_cause"), a.num("signals.prob_without_cause")

    # 1. Skeleton ---------------------------------------------------------------
    levels = _exact_labels(a.distribution("population.level"), n, rng)
    countries = _exact_labels(a.distribution("population.country"), n, rng)
    area_dist = a.distribution("population.area")
    ic_idx = np.where(levels != MANAGER_LEVEL)[0]
    mgr_idx = np.where(levels == MANAGER_LEVEL)[0]
    areas = np.empty(n, dtype=object)
    areas[ic_idx] = _exact_labels(area_dist, len(ic_idx), rng)

    reports = a.num("structure.reports_per_team_manager")
    teams_per_area = {ar: max(1, int(round((areas[ic_idx] == ar).sum() / reports))) for ar in area_dist}
    n_teams = sum(teams_per_area.values())
    if n_teams > len(mgr_idx):
        raise ValueError("Há mais times do que gestores: revise population.level.Gestor ou structure.reports_per_team_manager")
    team_ids, team_area = [], {}
    for ar, k in teams_per_area.items():
        for _ in range(k):
            tid = f"T{len(team_ids) + 1:03d}"
            team_ids.append(tid)
            team_area[tid] = ar

    team_of = np.empty(n, dtype=object)
    for ar in area_dist:
        members = ic_idx[areas[ic_idx] == ar].copy()
        rng.shuffle(members)
        area_teams = [t for t in team_ids if team_area[t] == ar]
        for i, person in enumerate(members):
            team_of[person] = area_teams[i % len(area_teams)]

    mgr_shuffled = mgr_idx.copy()
    rng.shuffle(mgr_shuffled)
    team_managers, leaders = mgr_shuffled[:n_teams], mgr_shuffled[n_teams:]
    role = np.array([IC] * n, dtype=object)
    manager_of_team = {}
    for tid, person in zip(team_ids, team_managers):
        role[person], areas[person] = TEAM_MANAGER, team_area[tid]
        manager_of_team[tid] = person
    leaders_per_area = _allocate(teams_per_area, len(leaders)) if len(leaders) else {}
    leader_iter = iter(leaders)
    leaders_by_area = {}
    for ar, k in leaders_per_area.items():
        leaders_by_area[ar] = [next(leader_iter) for _ in range(k)]
        for person in leaders_by_area[ar]:
            role[person], areas[person] = LEADER, ar

    ids = np.array([f"C{i + 1:04d}" for i in range(n)], dtype=object)
    names = np.array([random_name(rng, c) for c in countries], dtype=object)
    manager_id = np.empty(n, dtype=object)
    for person in ic_idx:
        manager_id[person] = ids[manager_of_team[team_of[person]]]
    superior_of_team = {}
    for i, tid in enumerate(team_ids):
        area_leaders = leaders_by_area.get(team_area[tid], [])
        superior = ids[area_leaders[i % len(area_leaders)]] if area_leaders else None
        superior_of_team[tid] = superior
        manager_id[manager_of_team[tid]] = superior

    # 2. Hidden cause -----------------------------------------------------------
    k_problem = int(round(a.num("cause.manager.team_share") * n_teams))
    problem_teams = set(rng.choice(team_ids, size=k_problem, replace=False)) if k_problem else set()
    member_prob = a.num("cause.manager.member_prob")
    in_problem_team = np.array([role[i] == IC and team_of[i] in problem_teams for i in range(n)])
    expected_manager_share = member_prob * in_problem_team.sum() / n
    other = {
        "remuneração": a.num("cause.compensation"),
        "crescimento": a.num("cause.growth"),
        EXTERNAL: a.num("cause.external"),
    }
    scale = 1 / (1 - expected_manager_share)
    probs = {k: v * scale for k, v in other.items()}
    probs[NO_CAUSE] = 1 - sum(probs.values())
    cause = np.empty(n, dtype=object)
    for i in range(n):
        if in_problem_team[i] and rng.random() < member_prob:
            cause[i] = "gestor"
        else:
            cause[i] = rng.choice(list(probs), p=list(probs.values()))

    # 3. Active signals ---------------------------------------------------------
    drawn = pd.DataFrame(index=ids)
    team_signal_state = {}
    for _, s in signals.iterrows():
        if s["level"] == "pessoa":
            p = np.where(cause == s["component"], p_with, p_without)
            drawn[s["signal"]] = rng.random(n) < p
        else:
            state = {t: rng.random() < (p_with if t in problem_teams else p_without) for t in team_ids}
            team_signal_state[s["signal"]] = state
            drawn[s["signal"]] = [role[i] == IC and state[team_of[i]] for i in range(n)]

    # 4. Raw data ---------------------------------------------------------------
    medians = a.group("market.median")
    factors = a.group("market.country_factor")
    thr = a.num("signals.compa_threshold")
    cmean, csd, cmin, cmax = (a.num(f"pay.compa_{k}") for k in ("mean", "sd", "min", "max"))
    no_raise_days = a.num("signals.no_raise_months") * DAYS_PER_MONTH
    ref_years = a.group("signals.time_in_level_ref")
    multiple = a.num("signals.time_in_level_multiple")
    years = milestones(a)
    window_days = a.num("signals.milestone_window_months") * DAYS_PER_MONTH
    tmin_days = a.num("structure.tenure_min_months") * DAYS_PER_MONTH
    tmax_days = a.num("structure.tenure_max_months") * DAYS_PER_MONTH
    change_days = a.num("signals.manager_change_months") * DAYS_PER_MONTH
    max_no_raise_days = a.num("generation.max_months_without_raise") * DAYS_PER_MONTH
    tl_extra_days = a.num("generation.time_in_level_extra_months") * DAYS_PER_MONTH
    max_change_days = a.num("generation.max_months_since_manager_change") * DAYS_PER_MONTH

    # Team manager start dates (team-level signal: manager change)
    team_start_days = {}
    for tid in team_ids:
        if team_signal_state["manager_change"][tid]:
            team_start_days[tid] = rng.uniform(15, change_days - 10)
        else:
            team_start_days[tid] = rng.uniform(change_days + 10, max_change_days)
    start_needed = {manager_of_team[t]: d for t, d in team_start_days.items()}

    rows, events = [], []
    for i in range(n):
        sig = drawn.iloc[i]
        compa = (
            _trunc_normal(rng, cmean, csd, cmin, thr - 0.003)
            if sig["compa_below"]
            else _trunc_normal(rng, cmean, csd, thr + 0.003, cmax)
        )
        median = medians[levels[i]] * factors[countries[i]]
        cost = round(compa * median, -2)

        level_thr = ref_years[levels[i]] * multiple * DAYS_PER_YEAR
        tl = rng.uniform(level_thr + 10, level_thr + tl_extra_days) if sig["time_in_level"] else None
        if sig["no_raise"]:
            upper = min(max_no_raise_days, tl if tl is not None else level_thr - 10)
            mr = rng.uniform(no_raise_days + 10, upper)
        else:
            mr = rng.uniform(30, no_raise_days - 10)
        if tl is None:
            tl = rng.uniform(max(mr, 30), level_thr - 10) if max(mr, 30) < level_thr - 10 else mr
        min_tenure = max(tl, start_needed.get(i, 0), tmin_days)

        if sig["tenure_milestone"]:
            options = []
            for m in years:
                hire = (t0 + pd.Timedelta(days=int(rng.uniform(5, window_days - 5)))) - pd.DateOffset(years=m)
                if (t0 - hire).days >= min_tenure:
                    options.append(hire)
            if not options:
                raise ValueError(f"Sem marco de tempo de casa compatível para {ids[i]}")
            hire = options[rng.integers(len(options))]
        else:
            for _ in range(100):
                hire = _days_ago(t0, rng.uniform(min_tenure, max(tmax_days, min_tenure + 30)))
                if not milestone_active(hire, t0, years, window_days):
                    break
            else:
                raise ValueError(f"Não foi possível evitar um marco de tempo de casa para {ids[i]}")
        hire = hire.normalize()
        promo = max(_days_ago(t0, tl), hire)
        pay_change = max(_days_ago(t0, mr), hire)

        rows.append(
            dict(
                employee_id=ids[i], name=names[i], country=countries[i], area=areas[i],
                team_id=team_of[i] if role[i] == IC else (
                    next((t for t, p in manager_of_team.items() if p == i), None)),
                level=levels[i], role=role[i], manager_id=manager_id[i],
                hire_date=hire.date(), last_promotion_date=promo.date(), last_pay_change_date=pay_change.date(),
                annual_cost_brl=cost, status="ativo", exit_date=None, exit_type=None, regretted=None,
            )
        )
        events.append(dict(employee_id=ids[i], date=hire.date(), event="admissão", detail=""))
        if promo > hire + pd.Timedelta(days=30):
            events.append(dict(employee_id=ids[i], date=promo.date(), event="promoção", detail=f"para {levels[i]}"))
        if pay_change > promo + pd.Timedelta(days=1):
            events.append(dict(employee_id=ids[i], date=pay_change.date(), event="reajuste", detail=""))

    hris = pd.DataFrame(rows)
    hire_by_id = dict(zip(hris["employee_id"], pd.to_datetime(hris["hire_date"])))
    for tid in team_ids:
        start = _days_ago(t0, team_start_days[tid])
        for i in np.where((team_of == tid) & (role == IC))[0]:
            if hire_by_id[ids[i]] < start:
                events.append(dict(employee_id=ids[i], date=start.date(), event="troca de gestor",
                                   detail=f"novo gestor: {ids[manager_of_team[tid]]}"))

    # 5. Exit history -----------------------------------------------------------
    p_no, p_yes = a.num("exit.annual_prob_no_cause"), a.num("exit.annual_prob_with_cause")
    expected_turnover = float(np.mean(np.where(cause == NO_CAUSE, p_no, p_yes)))
    hist_days = a.num("history.months") * DAYS_PER_MONTH
    exit_window = a.num("signals.team_exits_window_months") * DAYS_PER_MONTH
    exits_min = a.int("signals.team_exits_min")
    n_hist = int(round(n * expected_turnover * a.num("history.months") / 12))
    n_recent = int(round(n_hist * exit_window / hist_days))

    exit_rows = []  # (team_id, days_ago)
    hot = [t for t in team_ids if team_signal_state["team_exits"][t]]
    cold = [t for t in team_ids if not team_signal_state["team_exits"][t]]
    for t in hot:
        for _ in range(int(rng.integers(exits_min, exits_min + 2))):
            exit_rows.append((t, rng.uniform(5, exit_window - 5)))
    remaining_recent = max(0, n_recent - len(exit_rows))
    per_cold_max = exits_min - 1
    cold_slots = [t for t in cold for _ in range(per_cold_max)]
    rng.shuffle(cold_slots)
    for t in cold_slots[:remaining_recent]:
        exit_rows.append((t, rng.uniform(5, exit_window - 5)))
    for _ in range(max(0, n_hist - len(exit_rows))):
        exit_rows.append((team_ids[rng.integers(len(team_ids))], rng.uniform(exit_window + 5, hist_days - 5)))

    ic_level_dist = {k: v for k, v in a.distribution("population.level").items() if k != MANAGER_LEVEL}
    ic_level_dist = {k: v / sum(ic_level_dist.values()) for k, v in ic_level_dist.items()}
    country_dist = a.distribution("population.country")
    regretted_share = a.num("exit.regretted_share")
    former_min = a.num("generation.former_tenure_min_months")
    former_max = a.num("generation.former_tenure_max_months")
    former = []
    for j, (tid, days) in enumerate(exit_rows):
        ctry = rng.choice(list(country_dist), p=list(country_dist.values()))
        lvl = rng.choice(list(ic_level_dist), p=list(ic_level_dist.values()))
        exit_date = _days_ago(t0, days)
        hire = (exit_date - pd.Timedelta(days=int(rng.uniform(former_min, former_max) * DAYS_PER_MONTH))).normalize()
        compa = _trunc_normal(rng, cmean, csd, cmin, cmax)
        eid = f"X{j + 1:04d}"
        former.append(
            dict(
                employee_id=eid, name=random_name(rng, ctry), country=ctry, area=team_area[tid], team_id=tid,
                level=lvl, role=IC, manager_id=ids[manager_of_team[tid]], hire_date=hire.date(),
                last_promotion_date=hire.date(), last_pay_change_date=hire.date(),
                annual_cost_brl=round(compa * medians[lvl] * factors[ctry], -2), status="desligado",
                exit_date=exit_date.date(), exit_type="voluntário", regretted=bool(rng.random() < regretted_share),
            )
        )
        events.append(dict(employee_id=eid, date=hire.date(), event="admissão", detail=""))
        events.append(dict(employee_id=eid, date=exit_date.date(), event="desligamento voluntário", detail=""))
    hris = pd.concat([hris, pd.DataFrame(former)], ignore_index=True)

    # Pulse and context ---------------------------------------------------------
    pulse_max = a.int("signals.pulse_max_score")
    pulse = pd.DataFrame(
        dict(
            employee_id=ids,
            date=[_days_ago(t0, rng.uniform(3, 30)).date() for _ in range(n)],
            question="Tenho clareza e apoio do meu gestor",
            score=[int(rng.integers(1, pulse_max + 1)) if s else int(rng.integers(pulse_max + 1, 6))
                   for s in drawn["pulse_manager"]],
        )
    )
    ctx_window = a.num("signals.context_window_months") * DAYS_PER_MONTH
    neutral_share = a.num("generation.neutral_context_share")
    context = []

    def add_context(i, event, source, component):
        text = rng.choice(CONTEXT_TEMPLATES[event]).format(project=rng.choice(PROJECTS), name=names[i].split()[0])
        context.append(dict(employee_id=ids[i], date=_days_ago(t0, rng.uniform(5, ctx_window - 5)).date(),
                            source=source, text=text, extracted_event=event, component=component))

    for i in range(n):
        if drawn.iloc[i]["external_offer"]:
            add_context(i, "proposta_externa", "nota de conversa de carreira", "remuneração")
        if drawn.iloc[i]["growth_request"]:
            if rng.random() < a.num("generation.project_end_share"):
                add_context(i, "fim_de_projeto_sem_escopo", "ata de projeto", "crescimento")
            else:
                add_context(i, "pedido_crescimento_sem_plano", "nota de conversa de carreira", "crescimento")
        if not (drawn.iloc[i]["external_offer"] or drawn.iloc[i]["growth_request"]) and rng.random() < neutral_share:
            add_context(i, "neutro", "nota de conversa de carreira", "")
    context = pd.DataFrame(context)
    context.insert(0, "context_id", [f"K{i + 1:04d}" for i in range(len(context))])

    # Managers and benchmark ----------------------------------------------------
    mgr_rows = []
    for tid in team_ids:
        p = manager_of_team[tid]
        mgr_rows.append(dict(manager_id=ids[p], name=names[p], area=team_area[tid], team_id=tid, role=TEAM_MANAGER,
                             superior_id=superior_of_team[tid], n_reports=int(((team_of == tid) & (role == IC)).sum()),
                             team_start_date=_days_ago(t0, team_start_days[tid]).date()))
    for ar, people in leaders_by_area.items():
        for p in people:
            mgr_rows.append(dict(manager_id=ids[p], name=names[p], area=ar, team_id=None, role=LEADER,
                                 superior_id=None, n_reports=int((manager_id == ids[p]).sum()), team_start_date=None))
    managers = pd.DataFrame(mgr_rows)

    benchmark = pd.DataFrame(
        [dict(area=ar, level=lvl, country=c, median_annual_brl=round(medians[lvl] * factors[c], -2))
         for ar in area_dist for lvl in medians for c in factors]
    )

    world = World()
    world.public = dict(
        hris=hris,
        events=pd.DataFrame(events).sort_values(["date", "employee_id"]).reset_index(drop=True),
        benchmark=benchmark,
        managers=managers,
        pulse=pulse,
        context=context,
    )
    world.hidden = dict(
        truth=pd.DataFrame(dict(employee_id=ids, cause=cause, in_problem_team=in_problem_team)).join(
            drawn.reset_index(drop=True)
        ),
        problem_teams=pd.DataFrame(dict(team_id=sorted(problem_teams))),
    )
    world.notes = dict(expected_turnover=expected_turnover, expected_manager_share=expected_manager_share)

    # 6. Network ----------------------------------------------------------------
    comp_of = dict(zip(signals["signal"], signals["component"]))
    per_cause = np.stack([drawn[[s for s in drawn.columns if comp_of[s] == c]].sum(axis=1) for c in CAUSES], axis=1)
    case_rate = float((per_cause.max(axis=1) >= a.int("case.min_signals_same_cause")).mean())
    world.notes["case_rate"] = case_rate
    network, network_truth, companies = generate_network(a, rng, expected_manager_share, case_rate)
    world.public["network_companies"] = companies
    world.public["network_cases"] = network
    world.hidden["network_truth"] = network_truth
    return world


def intervention_effect(a: Assumptions, intervention: str, true_cause: str) -> float:
    """Reduction in exit probability: right cause, wrong cause, or no action."""
    target = a.interventions.set_index("intervention").loc[intervention, "target_cause"]
    if target == "":
        return 0.0
    return a.num("intervention.effect_right") if target == true_cause else a.num("intervention.effect_wrong")


def intervention_cost(a: Assumptions, intervention: str, annual_cost: float) -> float:
    row = a.interventions.set_index("intervention").loc[intervention]
    value = a.num(row["cost_key"])
    return round(value * annual_cost, -2) if row["cost_rule"] == "share_of_annual_cost" else value


def _trunc_normal_vec(rng, mean, sd, lo, hi) -> np.ndarray:
    """Vectorized truncated normal: rejection sampling, uniform fallback for the rare leftovers."""
    lo, hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)
    x = rng.normal(mean, sd, lo.shape)
    bad = (x < lo) | (x > hi)
    for _ in range(50):
        if not bad.any():
            break
        x[bad] = rng.normal(mean, sd, bad.sum())
        bad = (x < lo) | (x > hi)
    x[bad] = rng.uniform(lo[bad], hi[bad])
    return x


def generate_network(a: Assumptions, rng, manager_share: float, case_rate: float):
    """Closed cases at other Comp clients, generated by the same world rules (signals drawn per person).

    Network size follows from the assumptions: employees across the client base x the share of employees
    with an open case (observed in the generated client) x the years of decisions with a known outcome.
    """
    t0 = a.date("general.reference_date")
    signals = a.signals
    p_with, p_without = a.num("signals.prob_with_cause"), a.num("signals.prob_without_cause")
    min_signals = a.int("case.min_signals_same_cause")
    n_companies = a.int("network.n_companies")
    max_months = a.num("network.months")
    min_months = a.num("generation.network_min_months_ago")

    country_dist = a.distribution("population.country")
    area_dist = a.distribution("population.area")
    level_dist = a.distribution("population.level")
    medians, factors = a.group("market.median"), a.group("market.country_factor")
    thr = a.num("signals.compa_threshold")
    cmean, csd, cmin, cmax = (a.num(f"pay.compa_{k}") for k in ("mean", "sd", "min", "max"))

    companies = pd.DataFrame(
        dict(
            company_id=[f"E{i + 1:03d}" for i in range(n_companies)],
            employees=rng.integers(a.int("generation.network_company_min_employees"),
                                   a.int("generation.network_company_max_employees") + 1, n_companies),
            hq_country=rng.choice(list(country_dist), size=n_companies, p=list(country_dist.values())),
            sector="SaaS B2B",
        )
    )
    years_of_decisions = (max_months - min_months) / 12
    n_cases = int(round(companies["employees"].sum() * case_rate * years_of_decisions))

    cause_probs = {"remuneração": a.num("cause.compensation"), "crescimento": a.num("cause.growth"),
                   "gestor": manager_share, EXTERNAL: a.num("cause.external")}
    cause_probs[NO_CAUSE] = 1 - sum(cause_probs.values())
    cause_labels = np.array(list(cause_probs), dtype=object)

    # Candidates are drawn in batches; only those whose signals open a case enter the network.
    sig_names = signals["signal"].tolist()
    sig_comp = signals["component"].to_numpy(dtype=object)
    causes, actives = [], []
    collected = 0
    while collected < n_cases:
        m = max(4 * (n_cases - collected), 1000)
        c = cause_labels[rng.choice(len(cause_labels), size=m, p=list(cause_probs.values()))]
        act = rng.random((m, len(sig_names))) < np.where(c[:, None] == sig_comp[None, :], p_with, p_without)
        counts = np.stack([act[:, sig_comp == k].sum(axis=1) for k in CAUSES], axis=1)
        keep = counts.max(axis=1) >= min_signals
        causes.append(c[keep])
        actives.append(act[keep])
        collected += keep.sum()
    cause = np.concatenate(causes)[:n_cases]
    active = np.concatenate(actives)[:n_cases]
    counts = np.stack([active[:, sig_comp == k].sum(axis=1) for k in CAUSES], axis=1)
    attributed = np.array(CAUSES, dtype=object)[counts.argmax(axis=1)]  # ties: first in CAUSES order

    inter = a.interventions
    by_cause = dict(zip(inter["target_cause"], inter["intervention"]))
    target_of = dict(zip(inter["intervention"], inter["target_cause"]))
    options = np.array(inter["intervention"].tolist(), dtype=object)
    recommended = np.array([by_cause[c] for c in attributed], dtype=object)
    right = np.array([by_cause.get(c, "") for c in cause], dtype=object)

    # Decision: follow the recommendation, or the status-quo choice.
    follows = rng.random(n_cases) < a.num("behavior.follow_recommendation")
    picks_right = (right != "") & (rng.random(n_cases) < a.num("behavior.status_quo_prob_right"))
    u = rng.random(n_cases)
    sq_choice = np.empty(n_cases, dtype=object)
    for i in range(n_cases):
        if picks_right[i]:
            sq_choice[i] = right[i]
        else:
            pool = options[options != right[i]]
            sq_choice[i] = pool[int(u[i] * len(pool))]
    chosen = np.where(follows, recommended, sq_choice)
    followed = chosen == recommended

    level = np.array(list(level_dist), dtype=object)[rng.choice(len(level_dist), n_cases, p=list(level_dist.values()))]
    country = np.array(list(country_dist), dtype=object)[rng.choice(len(country_dist), n_cases, p=list(country_dist.values()))]
    area = np.array(list(area_dist), dtype=object)[rng.choice(len(area_dist), n_cases, p=list(area_dist.values()))]
    below = active[:, sig_names.index("compa_below")]
    compa = _trunc_normal_vec(rng, cmean, csd, np.where(below, cmin, thr + 0.003), np.where(below, thr - 0.003, cmax))
    annual_cost = np.round(compa * np.array([medians[l] for l in level]) * np.array([factors[c] for c in country]), -2)

    # Outcome after 6 months.
    p_no, p_yes = a.num("exit.annual_prob_no_cause"), a.num("exit.annual_prob_with_cause")
    eff_right, eff_wrong = a.num("intervention.effect_right"), a.num("intervention.effect_wrong")
    target = np.array([target_of[x] for x in chosen], dtype=object)
    effect = np.where(target == "", 0.0, np.where(target == cause, eff_right, eff_wrong))
    p6_after = np.where(cause == NO_CAUSE, p_no, p_yes) / 2 * (1 - effect)
    stayed = rng.random(n_cases) >= p6_after
    treated = (chosen == right) | (cause == NO_CAUSE)
    perf_p = np.where(treated, a.num("outcome.performing_if_treated"), a.num("outcome.performing_if_untreated"))
    performing = stayed & (rng.random(n_cases) < perf_p)
    bias, noise = a.num("behavior.prediction_bias_pp") / 100, a.num("behavior.prediction_noise_pp") / 100
    prediction = np.clip(np.round((1 - p6_after + bias + rng.normal(0, noise, n_cases)) * 20) / 20, 0.05, 0.95)
    exit_month = np.where(stayed, np.nan, rng.integers(1, 7, n_cases))

    cost_rule = dict(zip(inter["intervention"], inter["cost_rule"]))
    cost_value = {k: a.num(v) for k, v in zip(inter["intervention"], inter["cost_key"])}
    cost = np.array([round(cost_value[x] * ac, -2) if cost_rule[x] == "share_of_annual_cost" else cost_value[x]
                     for x, ac in zip(chosen, annual_cost)])

    weights = companies["employees"] / companies["employees"].sum()
    days = rng.uniform(min_months * DAYS_PER_MONTH, max_months * DAYS_PER_MONTH, n_cases).round().astype(int)
    case_ids = [f"R{i + 1:06d}" for i in range(n_cases)]
    network = pd.DataFrame(
        dict(
            case_id=case_ids,
            company_id=companies["company_id"].to_numpy()[rng.choice(n_companies, n_cases, p=weights)],
            decision_date=(t0 - pd.to_timedelta(days, unit="D")).date,
            country=country, area=area, level=level, annual_cost_brl=annual_cost,
        )
    )
    for j, s in enumerate(sig_names):
        network[f"sig_{s}"] = active[:, j]
    network = network.assign(
        attributed_cause=attributed, recommended_intervention=recommended, intervention=chosen,
        followed_recommendation=followed, cost_brl=cost, manager_prediction_stay_6m=prediction,
        stayed_6m=stayed, performing_6m=performing, exit_month=pd.array(exit_month, dtype="Int64"),
    )
    truth = pd.DataFrame(dict(case_id=case_ids, true_cause=cause))
    return network, truth, companies
