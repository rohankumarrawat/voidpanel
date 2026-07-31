from django.apps import AppConfig


class DataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data'

    def ready(self):
        self._patch_sqlite_decimal_converter()

    @staticmethod
    def _patch_sqlite_decimal_converter():
        """
        Monkey-patch Django's SQLite Decimal converter to handle float/NULL
        values that cause decimal.InvalidOperation.

        Django 5.2's SQLite backend registers a type converter at the connection
        level. When DecimalField values are stored as float (e.g. 0.0 instead of
        '0.00') or NULL, the converter crashes with InvalidOperation. This patch
        wraps the converter in a try/except that returns Decimal('0') on failure.
        """
        import decimal
        try:
            from django.db.backends.sqlite3 import operations as sqlite_ops

            ops_class = sqlite_ops.DatabaseOperations
            _original = ops_class.get_decimalfield_converter

            def _safe_get_decimalfield_converter(self, *args, **kwargs):
                original_converter = _original(self, *args, **kwargs)
                if original_converter is None:
                    return original_converter

                def safe_converter(value, expression, connection):
                    if value is None:
                        return value
                    try:
                        return original_converter(value, expression, connection)
                    except (decimal.InvalidOperation, TypeError, ValueError):
                        try:
                            return decimal.Decimal(str(value))
                        except Exception:
                            return decimal.Decimal('0')

                return safe_converter

            ops_class.get_decimalfield_converter = _safe_get_decimalfield_converter
        except Exception:
            pass
