"""
SMTP backend compatible with Python 3.12+.

Django 3.2's built-in email backend calls ``starttls(keyfile=..., certfile=...)``,
which ``smtplib`` removed in Python 3.12. This subclass uses
``starttls(context=ssl.create_default_context())`` instead.

See: https://docs.python.org/3/whatsnew/3.12.html#smtplib
"""

import ssl

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME


class Py312CompatEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False

        connection_params = {"local_hostname": DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params["timeout"] = self.timeout
        if self.use_ssl:
            context = ssl.create_default_context()
            if self.ssl_certfile and self.ssl_keyfile:
                context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
            connection_params["context"] = context
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            if not self.use_ssl and self.use_tls:
                self.connection.starttls(context=ssl.create_default_context())
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
        return None
