from functools import wraps
from flask import redirect, url_for
from flask_login import current_user

# Example placeholder if further custom role checks are added.

def login_required_custom(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapped_view
