import requests
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Wholesale prices in INR per year for common TLDs (simulated / will be replaced by real API)
TLD_BASE_PRICES_INR = {
    '.com':   Decimal('817'),
    '.in':    Decimal('499'),
    '.net':   Decimal('999'),
    '.org':   Decimal('749'),
    '.co.in': Decimal('399'),
    '.io':    Decimal('2999'),
    '.co':    Decimal('1999'),
    '.info':  Decimal('599'),
}


class ConnectResellerClient:
    """
    Interfaces with the ConnectReseller API for domain operations.
    All retail prices returned are in INR for data-price-inr compatibility.
    """
    BASE_URL = "https://api.connectreseller.com/ConnectReseller/api/v1"

    def __init__(self, api_key=None, reseller_id=None):
        from data.models import ConnectResellerConfig
        config = ConnectResellerConfig.objects.filter(is_active=True).first()
        self.api_key = api_key or (config.api_key if config else None)
        self.reseller_id = reseller_id or (config.reseller_id if config else None)
        self.margin = Decimal(config.margin_percentage) if config else Decimal(20)
        self.enabled = config is not None and bool(self.api_key)

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "APIKey": self.api_key
        }

    def _get_tld(self, domain_name):
        """Extract TLD from domain name. Handles multi-part TLDs like .co.in"""
        parts = domain_name.lower().strip().split('.')
        if len(parts) >= 3 and f".{parts[-2]}.{parts[-1]}" in TLD_BASE_PRICES_INR:
            return f".{parts[-2]}.{parts[-1]}"
        if len(parts) >= 2:
            return f".{parts[-1]}"
        return '.com'

    def _simulate_check(self, domain_name, tld=None):
        """Return a simulated INR-priced domain check result."""
        if tld is None:
            tld = self._get_tld(domain_name)
        base_inr = TLD_BASE_PRICES_INR.get(tld, Decimal('999'))
        retail_inr = base_inr * (1 + self.margin / Decimal(100))
        return {
            "available": True,
            "domain": domain_name,
            "wholesale_price_inr": float(base_inr),
            "retail_price_inr": float(retail_inr.quantize(Decimal("1"))),
            "currency": "INR",
            "tld": tld,
        }

    def check_domain(self, domain_name):
        """
        Check if a domain is available, and return its wholesale & retail cost in INR.
        """
        if not self.enabled:
            return {"error": "Domain API is not configured or disabled. Please set it up in Super Admin → Domain API."}

        tld = self._get_tld(domain_name)
        try:
            # Fallback to simulation ONLY if API key is empty/demo key, not based on settings.DEBUG
            if self.api_key in ("demo_key", "", None):
                return self._simulate_check(domain_name, tld)

            # Correct ConnectReseller ESHOP API endpoint
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/checkdomainavailable"
            response = requests.get(url, params={"APIKey": self.api_key, "websiteName": domain_name}, timeout=10)

            if response.status_code != 200:
                logger.error(f"ConnectReseller checkDomain returned status {response.status_code}: {response.text}")
                return {"error": f"ConnectReseller API returned status {response.status_code}: {response.text}", "available": False, "domain": domain_name}

            data = response.json()
            response_msg = data.get("responseMsg", {})
            status_code = response_msg.get("statusCode", 400)
            
            # statusCode 200 means the domain is available for registration
            is_available = (status_code == 200)

            # Extract pricing if returned in responseData
            base_inr = TLD_BASE_PRICES_INR.get(tld, Decimal('999'))
            response_data = data.get("responseData")
            if isinstance(response_data, dict):
                fee = response_data.get('registrationFee') or response_data.get('price')
                if fee is not None:
                    try:
                        price_val = Decimal(str(fee))
                        if price_val > 0:
                            # If the registrar returned a small number, it might be USD — convert to INR
                            if price_val < 100:
                                base_inr = price_val * Decimal('85')
                            else:
                                base_inr = price_val
                    except Exception:
                        pass

            retail_inr = base_inr * (1 + self.margin / Decimal(100))

            return {
                "available": is_available,
                "domain": domain_name,
                "wholesale_price_inr": float(base_inr.quantize(Decimal("1"))),
                "retail_price_inr": float(retail_inr.quantize(Decimal("1"))),
                "currency": "INR",
                "tld": tld,
            }
        except Exception as e:
            logger.error(f"ConnectReseller check failed: {e}")
            return {"error": f"ConnectReseller check failed: {str(e)}", "available": False, "domain": domain_name}

    def check_bulk(self, base_name, tlds=None):
        """
        Check availability of base_name across multiple TLDs.
        Returns a list of results.
        """
        if tlds is None:
            tlds = ['.com', '.in', '.net', '.org', '.co.in', '.io']

        results = []
        for tld in tlds:
            # Build domain: strip existing TLD from base_name first
            name_parts = base_name.split('.')
            sld = name_parts[0]  # second level domain
            full_domain = f"{sld}{tld}"
            result = self.check_domain(full_domain)
            if 'error' not in result:
                results.append(result)
            else:
                # If we have a real API key configured, propagate the error directly
                # to inform the user/admin (e.g. 401 Unauthorized or IP whitelist issue)
                if self.api_key not in ("demo_key", "", None):
                    return {"error": result['error']}
                # Otherwise, fallback to simulation for demo mode
                results.append(self._simulate_check(full_domain, tld))
        return results

    def register_domain(self, domain_name, user_info, years=1):
        """Registers a domain name using the API."""
        if not self.enabled:
            return {"success": False, "error": "API not configured."}

        try:
            if self.api_key in ("demo_key", "", None):
                return {"success": True, "transaction_id": "SIM-847294", "domain": domain_name}

            # Correct ConnectReseller ESHOP API domain order endpoint
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/domainorder"
            payload = {
                "APIKey": self.api_key,
                "Websitename": domain_name,
                "ProductType": 1,
                "Duration": years,
                "ns1": "ns1.voidpanel.com",
                "ns2": "ns2.voidpanel.com"
            }
            response = requests.get(url, params=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                response_msg = data.get("responseMsg", {})
                status_code = response_msg.get("statusCode", 400)
                if status_code == 200:
                    return {"success": True, "api_response": data}
                else:
                    return {"success": False, "error": response_msg.get("message", "Registration failed.")}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"ConnectReseller register failed: {e}")
            return {"success": False, "error": str(e)}
