"""
Stage 5 (Optimize): NSGA-II genetic algorithm that searches over the
FARMER-CONTROLLABLE levers (N, P, K, irrigation) to find the Pareto
frontier that maximizes yield & profit while minimizing cost -- exactly
as described in the deck ("NSGA-II / Genetic Algorithm ... Maximize
yield, Maximize profit, Minimize cost").

Everything else in the farm profile (crop, soil, region, climate) is
held fixed -- those aren't decisions a farmer makes mid-season.
"""
import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize as pymoo_minimize

from . import model as model_module

# Search bounds for the 4 controllable decision variables
BOUNDS = {
    "nitrogen_kg_per_acre": (10, 200),
    "phosphorus_kg_per_acre": (5, 150),
    "potassium_kg_per_acre": (5, 150),
    "irrigation_mm_per_week": (0, 100),
}
DECISION_VARS = list(BOUNDS.keys())


class FarmOptimizationProblem(Problem):
    """3 objectives, all converted to MINIMIZE (pymoo convention):
       f1 = -predicted_yield   (i.e. maximize yield)
       f2 = -predicted_profit  (i.e. maximize profit)
       f3 = estimated_cost     (minimize cost directly)
    """

    def __init__(self, base_profile: dict):
        self.base_profile = base_profile
        xl = np.array([BOUNDS[v][0] for v in DECISION_VARS])
        xu = np.array([BOUNDS[v][1] for v in DECISION_VARS])
        super().__init__(n_var=len(DECISION_VARS), n_obj=3, n_constr=0, xl=xl, xu=xu)

    def _evaluate(self, X, out, *args, **kwargs):
        n = X.shape[0]
        f = np.zeros((n, 3))
        for i in range(n):
            profile = dict(self.base_profile)
            for j, var in enumerate(DECISION_VARS):
                profile[var] = float(X[i, j])

            yield_val = model_module.predict_yield(profile)
            _, cost, profit = model_module.economics(profile, yield_val)

            f[i, 0] = -yield_val
            f[i, 1] = -profit
            f[i, 2] = cost
        out["F"] = f


def run_optimization(base_profile: dict, n_generations: int = 40, population_size: int = 40, lang: str = "en"):
    problem = FarmOptimizationProblem(base_profile)
    algorithm = NSGA2(pop_size=population_size)

    res = pymoo_minimize(
        problem,
        algorithm,
        ("n_gen", n_generations),
        seed=42,
        verbose=False,
    )

    pareto_points = []
    for x, f in zip(res.X, res.F):
        profile = dict(base_profile)
        for j, var in enumerate(DECISION_VARS):
            profile[var] = float(x[j])
        yield_val = -f[0]
        profit_val = -f[1]
        cost_val = f[2]
        pareto_points.append({
            "nitrogen_kg_per_acre": round(profile["nitrogen_kg_per_acre"], 1),
            "phosphorus_kg_per_acre": round(profile["phosphorus_kg_per_acre"], 1),
            "potassium_kg_per_acre": round(profile["potassium_kg_per_acre"], 1),
            "irrigation_mm_per_week": round(profile["irrigation_mm_per_week"], 1),
            "predicted_yield_quintal_per_acre": round(float(yield_val), 2),
            "estimated_cost": round(float(cost_val), 2),
            "estimated_profit": round(float(profit_val), 2),
        })

    # De-duplicate near-identical points, sort by profit desc
    pareto_points.sort(key=lambda p: p["estimated_profit"], reverse=True)

    # Recommended = highest-profit point on the frontier (a simple, explainable
    # default selection rule; the frontend could let users pick a different
    # point from the frontier for a different risk/yield trade-off).
    recommended = pareto_points[0]

    baseline_yield = model_module.predict_yield(base_profile)
    _, baseline_cost, baseline_profit = model_module.economics(base_profile, baseline_yield)

    yield_change = recommended["predicted_yield_quintal_per_acre"] - baseline_yield
    profit_change = recommended["estimated_profit"] - baseline_profit
    cost_change = recommended["estimated_cost"] - baseline_cost

    if lang == "hi":
        summary = (
            f"सुझाव: नाइट्रोजन={recommended['nitrogen_kg_per_acre']}किग्रा, "
            f"फॉस्फोरस={recommended['phosphorus_kg_per_acre']}किग्रा, "
            f"पोटाश={recommended['potassium_kg_per_acre']}किग्रा/एकड़, "
            f"सिंचाई={recommended['irrigation_mm_per_week']}मिमी/सप्ताह -> "
            f"वर्तमान योजना की तुलना में "
            f"{'+' if yield_change >= 0 else ''}{yield_change:.1f} क्विंटल/एकड़ उपज, "
            f"{'+' if cost_change >= 0 else ''}₹{cost_change:.0f} लागत, "
            f"{'+' if profit_change >= 0 else ''}₹{profit_change:.0f} मुनाफा।"
        )
    else:
        summary = (
            f"Recommended: N={recommended['nitrogen_kg_per_acre']}kg, "
            f"P={recommended['phosphorus_kg_per_acre']}kg, "
            f"K={recommended['potassium_kg_per_acre']}kg/acre, "
            f"irrigation={recommended['irrigation_mm_per_week']}mm/week -> "
            f"{'+' if yield_change >= 0 else ''}{yield_change:.1f} quintal/acre yield, "
            f"{'+' if cost_change >= 0 else ''}₹{cost_change:.0f} cost, "
            f"{'+' if profit_change >= 0 else ''}₹{profit_change:.0f} profit vs. current plan."
        )

    return pareto_points, recommended, summary
