#!/usr/bin/env python3
"""Keep downstream examples on the public executable boundary."""

from __future__ import print_function

import re
import sys
from pathlib import Path


EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_FILES = {
    "sh/signal_health.sh": ("kdebug",),
    "sh/waveform_window.sh": ("kdebug",),
    "sh/module_connectivity.sh": ("kdebug",),
    "sh/coverage_convergence.sh": ("kcov",),
    "sh/regression_triage.sh": ("kdebug", "kcov"),
    "csh/signal_health.csh": ("kdebug",),
    "perl/signal_health.pl": ("kdebug",),
    "perl/waveform_window.pl": ("kdebug",),
    "py/signal_health.py": ("kdebug",),
}

FORBIDDEN = (
    ("private Tcl backend", re.compile(r"(?:kdebug|kcov)/(?:tcl_engine|libexec)|kdebug_npi[.]tcl|kcov_npi[.]tcl", re.I)),
    ("direct NPI Tcl call", re.compile(r"(?<![A-Za-z0-9_-])npi_[a-z][A-Za-z0-9_]*(?:[ \t]+-|[ \t]*[(])", re.I)),
    ("NPI runtime path", re.compile(r"NPIL1_PATH|share/NPI|LD_LIBRARY_PATH[^\n]*NPI", re.I)),
    ("NPI header or library build", re.compile(r"(?:npi(?:_[A-Za-z0-9]+)?[.]h|-[lL][^\s]*npi)", re.I)),
    ("direct Verdi Tcl execution", re.compile(r"\bverdi\b[^\n]*(?:-play|-ssv|-do)\b", re.I)),
    ("internal Python import", re.compile(r"^[ \t]*(?:from|import)[ \t]+(?:kdebug|kcov|kverif_mcp)(?:\b|[.])", re.I | re.M)),
)


def main():
    failures = []
    for relative, required_tools in sorted(WORKFLOW_FILES.items()):
        path = EXAMPLE_ROOT / relative
        if not path.is_file():
            failures.append("missing workflow: {0}".format(relative))
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                failures.append("{0}:{1}: {2}".format(relative, line, label))
        for tool in required_tools:
            if tool not in text:
                failures.append("{0}: does not invoke {1} executable".format(relative, tool))

    if failures:
        print("FAIL: CLI-only secondary-development boundary", file=sys.stderr)
        for failure in failures:
            print("  " + failure, file=sys.stderr)
        return 1

    print("PASS: CLI-only boundary ({0} workflows)".format(len(WORKFLOW_FILES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
