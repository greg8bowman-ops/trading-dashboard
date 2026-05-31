"""
education.py — Generates the daily learning section FROM the day's actual
analysis, not from canned lessons. Takes the regime read, the ranked setups,
and internals, and produces lesson text, vocabulary, and skill exercises that
reference what literally happened in today's scan.
"""

import numpy as np


VOCAB_BANK = {
    "ADX": ("Average Directional Index — measures trend STRENGTH (0-100), not direction. "
            "Above ~25 suggests a trend worth following; below ~20 suggests chop.",
            "Today the ADX reading drove whether trend or mean-reversion strategies were favoured."),
    "Expectancy": ("The average amount you expect to win/lose per trade: "
                   "(WinProb × AvgWin) − (LossProb × AvgLoss). Positive = edge.",
                   "Every ranked setup today was sorted by its modelled expectancy in R units."),
    "R-multiple": ("Profit or loss expressed in units of initial risk. Risking £10 and making £25 is +2.5R.",
                   "Targets today were set at fixed R-multiples of the stop distance."),
    "Relative Strength": ("How an instrument performs versus its peers. Leaders tend to keep leading short-term.",
                          "The scanner tilted win-probability toward the strongest names in the universe."),
    "ATR": ("Average True Range — typical daily range. Used to place stops beyond normal noise.",
            "Stops today were placed a multiple of ATR away from entry, not at arbitrary round numbers."),
    "Profit Factor": ("Gross profit ÷ gross loss. Above 1.0 is profitable; pros often target >1.5.",
                      "Shown in your performance tab once you log enough closed trades."),
    "Breadth": ("The share of instruments participating in a move. Strong breadth confirms a healthy trend.",
                "Today's breadth read informed the risk-on/risk-off tone."),
    "Mean Reversion": ("A strategy betting that stretched prices snap back to an average. Works in ranges, fails in trends.",
                       "Only eligible today on instruments with low ADX."),
}


def lesson_of_the_day(regime_label, internals, n_setups):
    bucket = regime_label.lower()
    if "strongly trend" in bucket:
        concept = "Trend Structure & Why You Don't Fade Strength"
        body = (
            f"Today's dominant read was **{regime_label}**. In strongly trending conditions, "
            "the highest-expectancy edge comes from joining the trend on pullbacks or continuation, "
            "NOT from picking tops/bottoms. Counter-trend mean-reversion setups were down-weighted "
            "precisely because ADX showed real directional energy. The lesson: let the regime pick "
            "the strategy, not the other way round."
        )
    elif "range" in bucket or "mean" in bucket:
        concept = "Range Conditions & Mean Reversion"
        body = (
            f"Today read as **{regime_label}**. With weak trend strength, breakouts tend to fail and "
            "fading the edges of the range carries the better expectancy. Notice the system refused "
            "to apply trend-following logic here — forcing a trend strategy into a range is a classic "
            "way to die by a thousand small losses."
        )
    else:
        concept = "Transitional Markets & The Value of Cash"
        body = (
            f"Today read as **{regime_label}** — neither cleanly trending nor cleanly ranging. "
            "This is the environment where most retail accounts bleed: signals conflict, and trading "
            "anyway means paying spread for low-conviction setups. The professional move is often to "
            "size down or stay flat. Cash is a position."
        )
    if n_setups == 0:
        body += (" Critically, zero setups cleared the checklist today — so the correct action is to "
                 "take no trade and protect capital.")
    return concept, body


def why_selected(ranked):
    if not ranked:
        return ("No trades were selected. Every candidate either had non-positive modelled "
                "expectancy, poor regime fit, or failed a checklist item. Not trading is itself "
                "a high-quality decision when no edge is present.")
    lines = []
    for i, t in enumerate(ranked, 1):
        lines.append(
            f"**#{i} {t['instrument']} ({t['direction']}, {t['strategy']})** ranked here because its "
            f"modelled expectancy was {t['ev_R']:+.2f}R with {t['win_prob']*100:.0f}% estimated win "
            f"probability and strong regime fit ({t['regime_fit']:.0%}). Lower-ranked or rejected "
            f"setups typically lacked regime alignment or had thinner reward-to-risk."
        )
    return "\n\n".join(lines)


def institutional_thinking(regime_label, risk_tone_label):
    return (
        f"A professional desk would start today by framing the environment — **{regime_label}**, "
        f"tone **{risk_tone_label}** — *before* looking at any single chart. They think in terms of "
        "portfolio heat (total risk on), not individual trade excitement. They are happy to do nothing. "
        "Their edge is not prediction; it is disciplined repetition of a positive-expectancy process "
        "across hundreds of trades, with ruthless loss control. They assume they will be wrong often "
        "and design position sizing so that being wrong is survivable."
    )


def mistakes_today(regime_label):
    bucket = regime_label.lower()
    common = [
        ("Risking too much per trade", "A 10% loss needs an 11% gain to recover; a 50% loss needs 100%. "
         "Pros cap risk at ~1% so no single trade can hurt them."),
        ("Moving or removing stops", "Retail traders 'give it room' and turn a 1R loss into a 5R disaster. "
         "The stop is the thesis-invalidation point — honour it."),
        ("Overtrading in poor conditions", "Boredom and the urge to 'do something' generate low-quality trades "
         "that bleed the account via costs and noise."),
    ]
    if "trend" in bucket:
        common.insert(0, ("Fading a strong trend", "Shorting strength / buying weakness in a trending market "
                          "fights the dominant flow. Today's ADX argued for going WITH the move."))
    elif "range" in bucket:
        common.insert(0, ("Chasing breakouts in a range", "Most breakouts in a range are false. Buying the top "
                          "of the range on a 'breakout' usually means buying right before the reversal."))
    return common


def skill_exercise(regime_label, ranked):
    if not ranked:
        level = "Intermediate"
        ex = ("Practice *doing nothing well*. Write one paragraph justifying why no-trade was correct "
              "today using the regime evidence. Learning to sit in cash is a genuine, underrated skill.")
    else:
        level = "Beginner → Intermediate"
        t = ranked[0]
        ex = (f"Manually recompute the position size for {t['instrument']}: with £1,000 equity and 1% risk "
              f"(£10), and a stop distance of {abs(t['entry']-t['stop']):.4f}, how many units? "
              "Do it by hand, then check against the Risk tab. Internalising the sizing math is foundational.")
    return level, ex


def vocab_for_today(regime_label, ranked):
    keys = ["Expectancy", "R-multiple", "ATR"]
    bl = regime_label.lower()
    if "trend" in bl:
        keys = ["ADX", "Relative Strength", "Expectancy"]
    elif "range" in bl or "mean" in bl:
        keys = ["Mean Reversion", "ADX", "R-multiple"]
    return [(k, *VOCAB_BANK[k]) for k in keys]
