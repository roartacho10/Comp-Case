"""Synthetic world generator.

Generation follows the causal order of the world:
1. skeleton (country, area, level, teams, managers)
2. hidden cause of risk
3. active signals, drawn from the cause
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
from src.names import unique_name
from src.prediction import scale
from src.signals import CAUSES, DAYS_PER_MONTH, DAYS_PER_YEAR, milestone_active, milestones

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
    taken_names = set(a.personas["name"])
    names = np.array([unique_name(rng, c, taken_names) for c in countries], dtype=object)
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
    probs = cause_probabilities(a)
    cause = np.array([rng.choice(list(probs), p=list(probs.values())) for _ in range(n)], dtype=object)

    # 3. Active signals ---------------------------------------------------------
    drawn = pd.DataFrame(index=ids)
    for _, s in signals.iterrows():
        p = np.where(cause == s["component"], p_with, p_without)
        drawn[s["signal"]] = rng.random(n) < p

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
    max_no_raise_days = a.num("generation.max_months_without_raise") * DAYS_PER_MONTH
    tl_extra_days = a.num("generation.time_in_level_extra_months") * DAYS_PER_MONTH

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
        min_tenure = max(tl, tmin_days)

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

    # 5. Exit history -----------------------------------------------------------
    p_no, p_yes = a.num("exit.annual_prob_no_cause"), a.num("exit.annual_prob_with_cause")
    expected_turnover = float(np.mean(np.where(cause == NO_CAUSE, p_no, p_yes)))
    hist_days = a.num("history.months") * DAYS_PER_MONTH
    n_hist = int(round(n * expected_turnover * a.num("history.months") / 12))
    exit_rows = [(team_ids[rng.integers(len(team_ids))], rng.uniform(5, hist_days - 5)) for _ in range(n_hist)]

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
                employee_id=eid, name=unique_name(rng, ctry, taken_names), country=ctry, area=team_area[tid], team_id=tid,
                level=lvl, role=IC, manager_id=ids[manager_of_team[tid]], hire_date=hire.date(),
                last_promotion_date=hire.date(), last_pay_change_date=hire.date(),
                annual_cost_brl=round(compa * medians[lvl] * factors[ctry], -2), status="desligado",
                exit_date=exit_date.date(), exit_type="voluntário", regretted=bool(rng.random() < regretted_share),
            )
        )
        events.append(dict(employee_id=eid, date=hire.date(), event="admissão", detail=""))
        events.append(dict(employee_id=eid, date=exit_date.date(), event="desligamento voluntário", detail=""))
    hris = pd.concat([hris, pd.DataFrame(former)], ignore_index=True)

    # Context -------------------------------------------------------------------
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
                             superior_id=superior_of_team[tid], n_reports=int(((team_of == tid) & (role == IC)).sum())))
    for ar, people in leaders_by_area.items():
        for p in people:
            mgr_rows.append(dict(manager_id=ids[p], name=names[p], area=ar, team_id=None, role=LEADER,
                                 superior_id=None, n_reports=int((manager_id == ids[p]).sum())))
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
        context=context,
    )
    world.hidden = dict(
        truth=pd.DataFrame(dict(employee_id=ids, cause=cause)).join(drawn.reset_index(drop=True)),
    )
    world.notes = dict(expected_turnover=expected_turnover)

    # 6. Network ----------------------------------------------------------------
    # Scripted personas replace three generated employees (data/personas.csv).
    from src.personas import apply_personas

    apply_personas(world, a)
    final = world.hidden["truth"]
    comp_of = dict(zip(signals["signal"], signals["component"]))
    per_cause = np.stack([final[[s for s in comp_of if comp_of[s] == c]].sum(axis=1) for c in CAUSES], axis=1)
    case_rate = float((per_cause.max(axis=1) >= a.int("case.min_signals_same_cause")).mean())
    world.notes["case_rate"] = case_rate
    network, network_truth, companies = generate_network(a, rng, case_rate)
    world.public["network_companies"] = companies
    world.public["network_cases"] = network
    world.hidden["network_truth"] = network_truth
    return world


def cause_probabilities(a: Assumptions) -> dict[str, float]:
    """Share of people with each hidden cause; the rest have no cause of risk."""
    probs = {"remuneração": a.num("cause.compensation"), "crescimento": a.num("cause.growth"),
             EXTERNAL: a.num("cause.external")}
    probs[NO_CAUSE] = 1 - sum(probs.values())
    return probs


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


def generate_network(a: Assumptions, rng, case_rate: float):
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
    window = a.num("outcome.window_months")
    min_months = window  # a case only closes after the outcome window

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

    cause_probs = cause_probabilities(a)
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

    # Outcome after the outcome window.
    p_no, p_yes = a.num("exit.annual_prob_no_cause"), a.num("exit.annual_prob_with_cause")
    eff_right, eff_wrong = a.num("intervention.effect_right"), a.num("intervention.effect_wrong")
    target = np.array([target_of[x] for x in chosen], dtype=object)
    effect = np.where(target == "", 0.0, np.where(target == cause, eff_right, eff_wrong))
    p_window = 1 - (1 - np.where(cause == NO_CAUSE, p_no, p_yes)) ** (window / 12)
    p_after = p_window * (1 - effect)
    stayed = rng.random(n_cases) >= p_after
    treated = (chosen == right) | (cause == NO_CAUSE)
    perf_p = np.where(treated, a.num("outcome.performing_if_treated"), a.num("outcome.performing_if_untreated"))
    performing = stayed & (rng.random(n_cases) < perf_p)
    under, noise = a.num("behavior.risk_underestimation"), a.num("behavior.prediction_noise_pp") / 100
    raw_prediction = 1 - p_after * (1 - under) + rng.normal(0, noise, n_cases)
    levels = np.array(sorted({v for _, v in scale(a)}, reverse=True))  # verbal scale (src/prediction.py)
    prediction = levels[np.abs(raw_prediction[:, None] - levels[None, :]).argmin(axis=1)]
    exit_month = np.where(stayed, np.nan, rng.integers(1, int(window) + 1, n_cases))

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
        followed_recommendation=followed, cost_brl=cost, manager_prediction_stay=prediction,
        stayed=stayed, performing=performing, exit_month=pd.array(exit_month, dtype="Int64"),
    )
    truth = pd.DataFrame(dict(case_id=case_ids, true_cause=cause))
    return network, truth, companies
