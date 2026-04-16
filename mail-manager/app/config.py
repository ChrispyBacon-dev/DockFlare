import os


def _env(key, default=''):
    return os.environ.get(key, default)


class _Config:
    @property
    def JWT_PUBLIC_KEY(self):
        return _env('JWT_PUBLIC_KEY')

    @property
    def JWT_ALGORITHM(self):
        return _env('JWT_ALGORITHM', 'EdDSA')

    @property
    def JWT_ISSUER(self):
        return _env('JWT_ISSUER', 'dockflare-master')

    @property
    def JWT_AUDIENCE(self):
        return _env('JWT_AUDIENCE', 'dockflare-mail')

    @property
    def WEBHOOK_SECRET(self):
        return _env('WEBHOOK_SECRET')

    @property
    def R2_ENDPOINT_URL(self):
        return _env('R2_ENDPOINT_URL')

    @property
    def R2_ACCESS_KEY_ID(self):
        return _env('R2_ACCESS_KEY_ID')

    @property
    def R2_SECRET_ACCESS_KEY(self):
        return _env('R2_SECRET_ACCESS_KEY')

    @property
    def R2_BUCKET_NAME(self):
        return _env('R2_BUCKET_NAME')

    @property
    def MAIL_DATA_PATH(self):
        return _env('MAIL_DATA_PATH', '/data')

    @property
    def OUTBOUND_WORKER_URL(self):
        return _env('OUTBOUND_WORKER_URL')

    @property
    def OUTBOUND_AUTH_SECRET(self):
        return _env('OUTBOUND_AUTH_SECRET')

    @property
    def DB_PATH(self):
        return os.path.join(self.MAIL_DATA_PATH, 'db', 'mail.db')

    @property
    def ATTACHMENTS_PATH(self):
        return os.path.join(self.MAIL_DATA_PATH, 'attachments')

    @property
    def APP_VERSION(self):
        return '3.1.0'


config = _Config()
config.IN_MAINTENANCE = False
