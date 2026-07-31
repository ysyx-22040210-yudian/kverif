#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def emit(payload):
    print(json.dumps(payload, separators=(",", ":")))


args = sys.argv[1:]
joined = " ".join(args)
if " actions" in " " + joined:
    emit(
        {
            "api_version": "kdebug.v1",
            "action": "actions",
            "ok": True,
            "data": {"actions": ["module.inspect", "signal.scan"]},
        }
    )
elif "module.inspect" in args:
    emit(
        {
            "api_version": "kdebug.v1",
            "action": "module.inspect",
            "ok": True,
            "summary": {
                "module": "npi_fixture_top.u_alu",
                "section_count": 3,
                "truncated": False,
            },
            "data": {
                "module": "npi_fixture_top.u_alu",
                "module_object": {
                    "object": {
                        "name": "u_alu",
                        "full_name": "npi_fixture_top.u_alu",
                        "def_name": "npi_fixture_alu",
                    }
                },
                "sections": {
                    "parameters": [
                        {
                            "object": {"name": "WIDTH", "size": 32, "local_param": 0},
                            "values": {"dec": "12"},
                        },
                        {
                            "object": {"name": "BIAS", "size": 12, "local_param": 0},
                            "values": {"dec": "1"},
                        },
                    ],
                    "ports": [
                        {"object": {"name": "lhs", "direction": "npiInput", "size": 12}},
                        {"object": {"name": "rhs", "direction": "npiInput", "size": 12}},
                        {"object": {"name": "result", "direction": "npiOutput", "size": 12}},
                    ],
                    "instances": [],
                },
            },
        }
    )
elif "signal.scan" in args:
    emit(
        {
            "api_version": "kdebug.v1",
            "action": "signal.scan",
            "ok": True,
            "summary": {"change_count": 5, "unknown_count": 0, "truncated": False},
            "data": {"changes": [{"time": "45ns", "value": "1"}]},
        }
    )
else:
    emit(
        {
            "api_version": "kdebug.v1",
            "ok": False,
            "error": {"code": "UNSUPPORTED_FAKE_COMMAND", "message": joined},
        }
    )
    raise SystemExit(1)
