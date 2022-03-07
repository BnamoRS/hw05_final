from datetime import date


def year(request):
    """Добавляет переменную с текущим годом."""
    current_date = date.today()
    return {'year': current_date.year}
