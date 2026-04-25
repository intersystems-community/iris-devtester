from iris_devtester.diagnostics import ConnectionDiagnosticError, _extract_sqlcode, build_diagnostic_error

_DIAGNOSTIC_SQLCODES = {-30, -23}


class DiagnosticCursor:
    def __init__(self, cursor, conn):
        self._cursor = cursor
        self._conn = conn

    def execute(self, operation, parameters=None):
        try:
            if parameters is None:
                return self._cursor.execute(operation)
            return self._cursor.execute(operation, parameters)
        except Exception as e:
            self._maybe_raise_diagnostic(e)

    def executemany(self, operation, seq_of_parameters):
        try:
            return self._cursor.executemany(operation, seq_of_parameters)
        except Exception as e:
            self._maybe_raise_diagnostic(e)

    def _maybe_raise_diagnostic(self, e: Exception):
        sqlcode = _extract_sqlcode(str(e))
        if sqlcode is not None and sqlcode in _DIAGNOSTIC_SQLCODES:
            raise build_diagnostic_error(e, self._conn, sqlcode) from e
        raise

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __iter__(self):
        return iter(self._cursor)

    def __enter__(self):
        self._cursor.__enter__()
        return self

    def __exit__(self, *args):
        return self._cursor.__exit__(*args)
