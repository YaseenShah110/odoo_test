import requests
import json
import time
import logging

_logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = '2024-04'


class ShopifyAPIClient:
    def __init__(self, shop_url, access_token):
        clean_url = shop_url.replace('https://', '').replace('http://', '').rstrip('/')
        self.shop_url = clean_url
        self.access_token = str(access_token).strip() if access_token else ''
        self.api_version = SHOPIFY_API_VERSION
        self.base_url = f"https://{self.shop_url}/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def _get_url(self, resource):
        return f"{self.base_url}/{resource}.json"

    def _do_request(self, method, resource, data=None, params=None, retries=3):
        url = self._get_url(resource)
        for attempt in range(retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=self.headers,
                                            params=params, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, headers=self.headers,
                                             data=json.dumps(data) if data else None,
                                             timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, headers=self.headers,
                                            data=json.dumps(data) if data else None,
                                            timeout=30)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=self.headers, timeout=30)
                else:
                    return False

                if response.status_code == 429:
                    retry_after = float(response.headers.get('Retry-After', 2.0))
                    _logger.warning(
                        f"Shopify rate limit hit. Retrying after {retry_after}s "
                        f"(attempt {attempt + 1}/{retries})"
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json() if response.status_code != 204 else True

            except requests.exceptions.HTTPError as e:
                resp = e.response
                _logger.error(
                    f"Shopify {method} HTTPError: {e} for url: {url}. "
                    f"Response: {resp.text if resp is not None else ''}"
                )
                err_msg = ""
                if resp is not None:
                    try:
                        err_data = resp.json()
                        if 'errors' in err_data:
                            errors = err_data['errors']
                            if isinstance(errors, dict):
                                err_msg = "; ".join([f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in errors.items()])
                            else:
                                err_msg = str(errors)
                    except Exception:
                        pass
                    if not err_msg:
                        err_msg = resp.text
                if not err_msg:
                    err_msg = str(e)
                from odoo.exceptions import UserError
                raise UserError(f"Shopify API Error ({resp.status_code if resp is not None else 'Unknown'}): {err_msg}")
            except requests.exceptions.Timeout:
                _logger.warning(
                    f"Shopify {method} timeout for {url}, attempt {attempt + 1}/{retries}"
                )
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return False
            except Exception as e:
                _logger.error(f"Shopify {method} error: {e} for url: {url}")
                return False
        return False

    def get(self, resource, params=None):
        return self._do_request('GET', resource, params=params)

    def post(self, resource, data):
        return self._do_request('POST', resource, data=data)

    def put(self, resource, data):
        return self._do_request('PUT', resource, data=data)

    def delete(self, resource):
        return self._do_request('DELETE', resource)

    def get_all_pages(self, resource, root_key, params=None):
        params = dict(params or {})
        params.setdefault('limit', 250)
        page_info = None

        while True:
            if page_info:
                req_params = {'limit': params['limit'], 'page_info': page_info}
            else:
                req_params = params

            result = self.get(resource, params=req_params)
            if not result or root_key not in result:
                break

            items = result[root_key]
            if not items:
                break

            yield items

            if len(items) < params['limit']:
                break

            if 'since_id' in params:
                params['since_id'] = items[-1]['id']
            else:
                break
