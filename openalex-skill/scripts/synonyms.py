SYNONYM_MAP = {
    "causal inference": ["causal identification", "causal effect", "endogeneity", "exogeneity", "内生性", "因果推断"],
    "endogeneity": ["endogenous", "内生性", "内生", "因果识别"],
    "内生性": ["endogeneity", "endogenous", "causal identification"],

    "difference-in-differences": ["DID", "staggered DID", "event study", "two-way fixed effects", "twoway fixed effects", "双重差分"],
    "DID": ["difference-in-differences", "event study", "双重差分"],
    "双重差分": ["DID", "difference-in-differences", "event study"],
    "parallel trend": ["common trend", "pre-trend", "parallel pre-trend", "平行趋势"],
    "event study": ["event-study", "event study design", "事件研究"],

    "regression discontinuity": ["RDD", "sharp RDD", "fuzzy RDD", "regression kink", "断点回归"],
    "RDD": ["regression discontinuity", "sharp RDD", "fuzzy RDD", "断点回归"],

    "instrumental variable": ["IV", "2SLS", "TSLS", "two-stage least squares", "GMM", "工具变量"],
    "IV": ["instrumental variable", "2SLS", "工具变量"],

    "matching": ["propensity score matching", "PSM", "coarsened exact matching", "CEM", "匹配"],
    "propensity score": ["propensity score matching", "PSM", "倾向得分"],

    "synthetic control": ["SCM", "synthetic DID", "augmented SCM", "synthetic difference-in-differences", "合成控制"],

    "machine learning": ["double machine learning", "DML", "causal forest", "causal random forest", "机器学习"],
    "causal forest": ["causal random forest", "causal tree", "grf", "generalized random forest"],
    "DML": ["double machine learning", "debiased machine learning"],

    "heterogeneity": ["heterogeneous treatment effect", "CATE", "subgroup analysis", "treatment effect heterogeneity", "异质性"],
    "heterogeneous treatment effect": ["HTE", "CATE", "conditional average treatment effect", "异质性处理效应"],

    "mechanism": ["mediation", "mediator", "channel", "moderator", "机制分析", "中介"],
    "mediation": ["mediating effect", "mediation analysis", "中介", "中介效应"],

    "robustness": ["robust", "sensitivity analysis", "placebo test", "falsification test", "permutation test", "稳健性"],
    "placebo test": ["falsification test", "permutation test", "randomization test", "安慰剂检验"],
    "稳健性": ["robustness", "sensitivity analysis", "placebo test", "falsification"],

    "panel data": ["longitudinal data", "fixed effects", "random effects", "面板数据"],
    "fixed effect": ["FE", "individual fixed effect", "time fixed effect", "固定效应"],
    "clustered standard error": ["cluster-robust", "clustered SE", "聚类标准误"],

    "selection bias": ["self-selection", "sample selection", "Heckman", "selection correction", "选择偏差"],

    "ATE": ["average treatment effect", "平均处理效应"],
    "ATT": ["average treatment effect on the treated", "处理组平均处理效应"],
    "LATE": ["local average treatment effect", "compiler average causal effect", "局部平均处理效应"],
    "marginal effect": ["marginal effect", "AME", "average marginal effect", "边际效应"],
    "interaction effect": ["interaction term", "moderation", "交互效应", "交互项"],
    "nonlinear": ["non-linear", "nonparametric", "semi-parametric", "非线性"],
    "publish bias": ["publication bias", "file drawer problem", "meta-analysis", "发表偏倚"],
}


def expand_query(query: str) -> list[str]:
    if not query or not query.strip():
        return [query]

    query_lower = query.strip().lower()

    lower_map = {k.lower(): v for k, v in SYNONYM_MAP.items()}

    if query_lower in lower_map:
        expanded = lower_map[query_lower]
        if query not in expanded:
            expanded = [query] + expanded
        else:
            expanded = [query] + [s for s in expanded if s.lower() != query_lower]
        return expanded[:6]

    for key, synonyms in lower_map.items():
        if key in query_lower:
            alternatives = [query]
            for syn in synonyms:
                if syn.lower() not in query_lower:
                    alt = query_lower.replace(key, syn)
                    if alt != query_lower:
                        alternatives.append(alt)
            return alternatives[:6]

    return [query]
