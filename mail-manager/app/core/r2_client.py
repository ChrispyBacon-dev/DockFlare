import threading
import boto3
from botocore.config import Config as BotoConfig
from app.config import config

_client_cache = {}
_cache_lock = threading.Lock()


def get_r2_client(access_key_id, secret_access_key, endpoint_url):
    cache_key = (endpoint_url, access_key_id)
    with _cache_lock:
        if cache_key not in _client_cache:
            _client_cache[cache_key] = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                config=BotoConfig(signature_version='s3v4'),
                region_name='auto'
            )
        return _client_cache[cache_key]


def _resolve(domain_cfg):
    if domain_cfg:
        return (
            domain_cfg['r2_access_key_id'],
            domain_cfg['r2_secret_access_key'],
            domain_cfg['r2_endpoint_url'],
            domain_cfg['r2_bucket'],
        )
    return (
        config.R2_ACCESS_KEY_ID,
        config.R2_SECRET_ACCESS_KEY,
        config.R2_ENDPOINT_URL,
        config.R2_BUCKET_NAME,
    )


def fetch_email_from_r2(r2_key, domain_cfg=None):
    ak, sk, ep, bucket = _resolve(domain_cfg)
    s3 = get_r2_client(ak, sk, ep)
    resp = s3.get_object(Bucket=bucket, Key=r2_key)
    return resp['Body'].read()


def delete_from_r2(r2_key, domain_cfg=None):
    ak, sk, ep, bucket = _resolve(domain_cfg)
    s3 = get_r2_client(ak, sk, ep)
    s3.delete_object(Bucket=bucket, Key=r2_key)
