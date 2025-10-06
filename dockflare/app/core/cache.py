# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# dockflare/app/core/cache.py
import logging
import os
import time
import threading
import redis
from flask_caching import Cache
from app import config

cache_config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300  # 5 minutes default
}

redis_url = os.getenv("REDIS_URL")
if redis_url:
    redis_db_index = config.REDIS_DB_INDEX

    if '/' in redis_url:
        base_url = redis_url.rsplit('/', 1)[0]
        final_redis_url = f"{base_url}/{redis_db_index}"
    else:
        final_redis_url = f"{redis_url}/{redis_db_index}"

    cache_config = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": final_redis_url,
        "CACHE_DEFAULT_TIMEOUT": 300,
        "CACHE_KEY_PREFIX": "dockflare_"
    }
    logging.info(f"Redis caching enabled with URL: {final_redis_url}")
else:
    logging.warning("Redis URL not provided. Using in-memory caching instead.")

cache = Cache(config=cache_config)

DNS_RECORDS_CACHE_TIMEOUT = int(os.getenv("DNS_RECORDS_CACHE_TIMEOUT", "300"))  # 5 minutes default
CACHE_REFRESH_INTERVAL = int(os.getenv("CACHE_REFRESH_INTERVAL", "3600"))  # 1 hour default
ENABLE_PERIODIC_CACHE_REFRESH = os.getenv("ENABLE_PERIODIC_CACHE_REFRESH", "true").lower() == "true"
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

_redis_client = None

def get_redis_client():
    global _redis_client
    cache_type = cache_config.get("CACHE_TYPE")

    if cache_type == "RedisCache":
        if _redis_client is None:
            try:
                redis_url = cache_config.get("CACHE_REDIS_URL")
                if not redis_url:
                    logging.error(f"get_redis_client: CACHE_REDIS_URL not found. cache_config keys: {list(cache_config.keys())}")
                    return None
                _redis_client = redis.from_url(redis_url)
                logging.info(f"Created dedicated Redis client for pub/sub from URL: {redis_url}")
            except Exception as e:
                logging.error(f"Failed to create Redis pub/sub client: {e}")
                return None
        return _redis_client
    else:
        logging.info(f"get_redis_client: Redis not configured (CACHE_TYPE={cache_type}), returning None")
    return None

def init_app(app):
    """Initialize the cache with the Flask app"""
    cache.init_app(app)
    logging.info(f"Cache initialized with type: {cache_config['CACHE_TYPE']}")

    if CACHE_ENABLED and ENABLE_PERIODIC_CACHE_REFRESH:
        schedule_periodic_cache_refresh()

def get_dns_records_cache_key(zone_id, tunnel_id):

    return f"dns_records:{zone_id}:{tunnel_id}"

def clear_dns_records_cache(zone_id=None, tunnel_id=None):

    if not CACHE_ENABLED:
        return
        
    if zone_id and tunnel_id:
        key = get_dns_records_cache_key(zone_id, tunnel_id)
        cache.delete(key)
        logging.debug(f"Cleared DNS records cache for zone {zone_id}, tunnel {tunnel_id}")
    elif zone_id:
        pattern = f"dns_records:{zone_id}:*"
        _delete_keys_by_pattern(pattern)
        logging.debug(f"Cleared all DNS records caches for zone {zone_id}")
    elif tunnel_id:
        pattern = f"dns_records:*:{tunnel_id}"
        _delete_keys_by_pattern(pattern)
        logging.debug(f"Cleared all DNS records caches for tunnel {tunnel_id}")
    else:
        pattern = "dns_records:*"
        _delete_keys_by_pattern(pattern)
        logging.debug("Cleared all DNS records caches")

def _delete_keys_by_pattern(pattern):
    
    if not CACHE_ENABLED:
        return
        
    try:

        if cache.config['CACHE_TYPE'] == 'RedisCache' and hasattr(cache, 'cache') and hasattr(cache.cache, '_client'):
            redis_client = cache.cache._client
            prefix = cache.config.get('CACHE_KEY_PREFIX', '')
            full_pattern = f"{prefix}{pattern}"
            cursor = '0'
            while cursor != 0:
                cursor, keys = redis_client.scan(cursor=cursor, match=full_pattern, count=100)
                if keys:
                    redis_client.delete(*keys)
                    logging.debug(f"Deleted {len(keys)} keys matching pattern {full_pattern}")
                cursor = int(cursor)
        else:
            logging.warning("Pattern-based cache invalidation is only supported with RedisCache")
    except Exception as e:
        logging.error(f"Error deleting keys by pattern {pattern}: {e}", exc_info=True)

def clear_zone_caches(zone_id=None):
    
    if not CACHE_ENABLED:
        return
        
    if zone_id:
        cache.delete(f"zone_details:{zone_id}")
        clear_dns_records_cache(zone_id=zone_id)
        logging.debug(f"Cleared all caches for zone {zone_id}")
    else:
        _delete_keys_by_pattern("zone_details:*")
        _delete_keys_by_pattern("zone_id:*")
        logging.debug("Cleared all zone caches")

def schedule_periodic_cache_refresh():
    
    if not CACHE_ENABLED:
        return
        
    def refresh_critical_caches():
    
        while True:
            try:
                logging.info("Performing periodic refresh of critical caches")
                clear_dns_records_cache()
                time.sleep(CACHE_REFRESH_INTERVAL)
            except Exception as e:
                logging.error(f"Error in periodic cache refresh: {e}", exc_info=True)
                time.sleep(60) 
        
    refresh_thread = threading.Thread(
        target=refresh_critical_caches,
        daemon=True,
        name="CacheRefreshThread"
    )
    refresh_thread.start()
    logging.info("Started periodic cache refresh thread")

def get_cache_stats():
        
    stats = {
        'connected': False,
        'dns_records_count': 0
    }
    
    if not CACHE_ENABLED:
        return stats
    
    try:
    
        if not hasattr(cache, 'config'):
            logging.warning("Cache not fully initialized yet when getting stats")
            return stats
    
        stats['connected'] = cache.config.get('CACHE_TYPE') == 'RedisCache'
        
        if stats['connected']:
            try:
                if hasattr(cache, 'cache') and hasattr(cache.cache, '_client'):
                    redis_client = cache.cache._client
                    redis_client.ping()
                else:
                    stats['connected'] = False
            except Exception as e:
                logging.error(f"Error connecting to Redis: {e}", exc_info=True)
                stats['connected'] = False
        
        if stats['connected'] and hasattr(cache, 'cache') and hasattr(cache.cache, '_client'):
            redis_client = cache.cache._client
            prefix = cache.config.get('CACHE_KEY_PREFIX', '')
            pattern = f"{prefix}dns_records:*"
            cursor = '0'
            dns_records_count = 0
            
            while cursor != 0:
                cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
                dns_records_count += len(keys)
                cursor = int(cursor)
                
            stats['dns_records_count'] = dns_records_count
        else:
            
            stats['dns_records_count'] = -1  
            
    except Exception as e:
        logging.error(f"Error getting cache stats: {e}", exc_info=True)
        
    return stats