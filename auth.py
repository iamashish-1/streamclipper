from functools import wraps
from flask import session, redirect

#-- Restricting access to certain routes.
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get("admin"):
            return f(*args, **kwargs)
        return redirect("/login")
    return wrap
