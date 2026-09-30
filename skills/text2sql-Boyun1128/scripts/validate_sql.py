#!/usr/bin/env python3
"""
validate_sql.py — Deterministic SQL validation harness for text2sql skill.

Usage:
    python validate_sql.py <sql_query> <schema_ddl>

Validates:
1. SQL is syntactically valid SQLite.
2. All referenced tables/columns exist in the schema.
3. Query is read-only (SELECT only, no DDL/DML).

Output: JSON to stdout
    {"valid": true/false, "error": "...", "details": {...}}
"""

import sys
import json
import sqlite3
import re


def is_read_only(sql: str) -> tuple[bool, str]:
    """Check if SQL is read-only (no DDL/DML statements)."""
    forbidden_patterns = [
        r'\b(CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|REPLACE|TRUNCATE)\b'
    ]
    sql_upper = sql.upper().strip()
    for pattern in forbidden_patterns:
        if re.search(pattern, sql_upper):
            return False, f"SQL contains forbidden statement matching: {pattern}"
    return True, ""


def validate_syntax(sql: str, schema_ddl: str) -> tuple[bool, str]:
    """Validate SQL syntax against schema using SQLite EXPLAIN."""
    con = sqlite3.connect(":memory:")
    try:
        # Create schema (empty tables)
        con.executescript(schema_ddl)
        # Validate SQL using EXPLAIN
        con.execute(f"EXPLAIN {sql}")
        return True, ""
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        con.close()


def check_multiple_statements(sql: str) -> tuple[bool, str]:
    """Check if SQL contains multiple statements."""
    # Remove comments and string literals for checking
    cleaned = re.sub(r'--[^\n]*', '', sql)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    # Split by semicolons and filter non-empty
    statements = [s.strip() for s in cleaned.split(';') if s.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements detected. Only one SELECT statement is allowed."
    return True, ""


def validate(schema_ddl: str, sql: str) -> tuple[bool, str]:
    """
    Validate SQL against schema. Returns (ok, error_message).
    Compatible with course test API: validate(schema, sql) -> (bool, str).
    """
    if not sql or not sql.strip():
        return False, "Empty SQL"

    # Check read-only
    is_ro, ro_err = is_read_only(sql)
    if not is_ro:
        return False, f"DDL/DML rejected: {ro_err}"

    # Check single statement
    is_single, single_err = check_multiple_statements(sql)
    if not is_single:
        return False, f"Multiple statements: {single_err}"

    # Check syntax against schema
    is_valid, syntax_err = validate_syntax(sql, schema_ddl)
    if not is_valid:
        return False, f"Syntax/schema error: {syntax_err}"

    return True, ""


def validate_full(sql: str, schema_ddl: str) -> dict:
    """Run all validations and return detailed result dict (used by main/CLI)."""
    result = {
        "valid": False,
        "error": "",
        "details": {
            "read_only": False,
            "single_statement": False,
            "syntax_valid": False
        }
    }

    # Check read-only
    is_ro, ro_err = is_read_only(sql)
    result["details"]["read_only"] = is_ro
    if not is_ro:
        result["error"] = f"Read-only check failed: {ro_err}"
        return result

    # Check single statement
    is_single, single_err = check_multiple_statements(sql)
    result["details"]["single_statement"] = is_single
    if not is_single:
        result["error"] = f"Single statement check failed: {single_err}"
        return result

    # Check syntax
    is_valid, syntax_err = validate_syntax(sql, schema_ddl)
    result["details"]["syntax_valid"] = is_valid
    if not is_valid:
        result["error"] = f"Syntax validation failed: {syntax_err}"
        return result

    result["valid"] = True
    return result


def main():
    if len(sys.argv) >= 3:
        sql = sys.argv[1]
        schema_ddl = sys.argv[2]
    elif len(sys.argv) == 2 and sys.argv[1].startswith('{'):
        # Single JSON argument
        try:
            input_data = json.loads(sys.argv[1])
            sql = input_data["sql"]
            schema_ddl = input_data["schema_ddl"]
        except (json.JSONDecodeError, KeyError) as e:
            print(json.dumps({"valid": False, "error": f"Invalid input: {e}", "details": {}}))
            sys.exit(1)
    else:
        # Check for --sql and --schema flags
        sql = None
        schema_ddl = None
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] in ('--sql', '-s') and i + 1 < len(sys.argv):
                sql = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] in ('--schema', '--schema_ddl', '-d') and i + 1 < len(sys.argv):
                schema_ddl = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        if not sql or not schema_ddl:
            # Read from stdin as JSON
            try:
                input_text = sys.stdin.read()
                if input_text.strip():
                    input_data = json.loads(input_text)
                    sql = input_data.get("sql", sql)
                    schema_ddl = input_data.get("schema_ddl", schema_ddl)
            except (json.JSONDecodeError, KeyError):
                pass

        if not sql or not schema_ddl:
            print(json.dumps({"valid": False, "error": "Usage: echo '{\"sql\": ..., \"schema_ddl\": ...}' | python validate_sql.py", "details": {}}))
            sys.exit(1)

    result = validate_full(sql, schema_ddl)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
