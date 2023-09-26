import functools
import logging
import settings as scraper_settings
import inspect
import traceback
import sys, os
# from metal_utils import send_email

ALREADY_SENT_ERROR_VIA_EMAIL = False


def decorate_module(module, decorator):
    for name, member in inspect.getmembers(module):
        if inspect.getmodule(member) == module and callable(member):
            if member == decorate_module or member == decorator:
                continue
            module.__dict__[name] = decorator(member)


def handle_exception(function):
    """
    A decorator that wraps the passed in function and logs
    exceptions should one occur
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            send_error_email_message(e, function)
            raise

    return wrapper


def send_error_email_message(exception, function=None):
    global ALREADY_SENT_ERROR_VIA_EMAIL
    if scraper_settings.SEND_ERRORS_VIA_EMAIL and not ALREADY_SENT_ERROR_VIA_EMAIL:
        filename = os.path.basename(sys.modules['__main__'].__file__)
        subject = '%s Error: %s' % (filename, exception)
        function_name = function.__name__ if function else 'N/A'
        str_traceback = traceback.format_exc()
        current_url = ''
        if hasattr(sys.modules['__main__'], 'driver') and hasattr(sys.modules['__main__'].driver, 'current_url'):
            current_url = sys.modules['__main__'].driver.current_url
        body = 'ERROR MESSAGE: %s\n\n' \
               'FILENAME: %s\n\n' \
               'FUNCTION NAME: %s\n\n' \
               'CURRENT_URL: %s\n\n' \
               'TRACEBACK: \n\n%s' % (exception, filename, function_name, current_url, str_traceback)
        # send_email(subject, body)
        # global ALREADY_SENT_ERROR_VIA_EMAIL
        ALREADY_SENT_ERROR_VIA_EMAIL = True
