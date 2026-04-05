import sys; from dateutil.parser import isoparse
def fix_cal():
    with open("zenith/tools/calendar.py", "r") as f:
        text = f.read()

    helper = """
def _parse_dt(dt):
    if isinstance(dt, str):
        from dateutil.parser import isoparse
        return isoparse(dt)
    return dt
"""
    if "_parse_dt" not in text:
        text = text.replace("import structlog\n", "import structlog\n" + helper)

    text = text.replace("if time_min is None:", "time_min = _parse_dt(time_min)\n        if time_min is None:")
    text = text.replace("if time_max is None:", "time_max = _parse_dt(time_max)\n        if time_max is None:")

    text = text.replace("service = self._get_service(credentials)\n\n        event_body = {",
                        "service = self._get_service(credentials)\n        start_time = _parse_dt(start_time)\n        end_time = _parse_dt(end_time)\n\n        event_body = {")

    text = text.replace("start_time = time_min.isoformat() + \"Z\"", "time_min = _parse_dt(time_min)\n            start_time = time_min.isoformat() + \"Z\"")
    text = text.replace("end_time = time_max.isoformat() + \"Z\"", "time_max = _parse_dt(time_max)\n            end_time = time_max.isoformat() + \"Z\"")

    with open("zenith/tools/calendar.py", "w") as f:
        f.write(text)

fix_cal()
