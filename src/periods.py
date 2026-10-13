"""Fixed periods of the prototype. They are definitions, not premises: every rate in the system refers to the
same 12 months (outcome of a decision, client history, turnover), so changing one alone would mix periods."""

OUTCOME_WINDOW_MONTHS = 12   # the outcome of each decision is measured 12 months later
HISTORY_MONTHS = 12          # months of client history before the reference date
