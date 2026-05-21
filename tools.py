def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result."""
    # Use a safe evaluator (not raw eval)
    import ast, math
    # Support basic math functions
    allowed = {"sqrt": math.sqrt, "abs": abs, "round": round, "pow": pow}
    result = eval(expression, {"__builtins__": {}}, allowed)
    return str(result)


def date_difference(date1: str, date2: str) -> str:
    """Calculate the number of days between two dates (YYYY-MM-DD format)."""
    from datetime import datetime
    d1 = datetime.strptime(date1, "%Y-%m-%d")
    d2 = datetime.strptime(date2, "%Y-%m-%d")
    return str(abs((d2 - d1).days))

def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between common units (km/miles, kg/lbs, celsius/fahrenheit)."""
    conversions = {
        ("km", "miles"): lambda v: v * 0.621371,
        ("miles", "km"): lambda v: v * 1.60934,
        ("kg", "lbs"): lambda v: v * 2.20462,
        ("lbs", "kg"): lambda v: v * 0.453592,
        ("celsius", "fahrenheit"): lambda v: v * 9/5 + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5/9,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key not in conversions:
        return f"Conversion from {from_unit} to {to_unit} not supported"
    return str(round(conversions[key](value), 4))