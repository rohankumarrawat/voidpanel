import requests
import socket
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)

# Fallback wholesale prices in INR (used only when TLDPrice table is empty)
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
        self.auto_provision = getattr(config, 'auto_provision_after_payment', False) if config else False

    def _get_tld(self, domain_name):
        """Extract TLD from domain name. Handles multi-part TLDs like .co.in"""
        parts = domain_name.lower().strip().split('.')
        if len(parts) >= 3 and f".{parts[-2]}.{parts[-1]}" in TLD_BASE_PRICES_INR:
            return f".{parts[-2]}.{parts[-1]}"
        if len(parts) >= 2:
            return f".{parts[-1]}"
        return '.com'

    def get_cached_price(self, tld):
        """
        Get retail price from TLDPrice cache table.
        Falls back to hardcoded prices if table is empty.
        """
        from data.models import TLDPrice
        try:
            entry = TLDPrice.objects.filter(tld=tld, is_active=True).first()
            if entry:
                return {
                    'wholesale_price_inr': float(entry.wholesale_price),
                    'retail_price_inr': float(entry.retail_price),
                }
        except Exception:
            pass

        # Fallback
        base = TLD_BASE_PRICES_INR.get(tld, Decimal('999'))
        retail = base * (1 + self.margin / Decimal(100))
        return {
            'wholesale_price_inr': float(base),
            'retail_price_inr': float(retail.quantize(Decimal('1'))),
        }

    def check_domain_fast(self, domain_name, skip_rdap=False):
        """
        Fast availability check using DNS lookup (~50-200ms).
        If DNS returns NXDOMAIN → domain is likely available.
        If DNS resolves → domain is taken.
        Price comes from the cached TLDPrice table.
        Set skip_rdap=True for bulk checks (DNS-only is fast enough).
        """
        tld = self._get_tld(domain_name)
        pricing = self.get_cached_price(tld)
        domain_name = domain_name.lower().strip()

        try:
            # DNS A record lookup — fast and free
            socket.setdefaulttimeout(2)
            try:
                socket.getaddrinfo(domain_name, None)
                # DNS resolved — domain exists (taken)
                is_available = False
            except socket.gaierror:
                # NXDOMAIN or no record — likely available
                is_available = True
            except socket.timeout:
                # Timeout — assume available (will be confirmed at checkout)
                is_available = True
        except Exception:
            is_available = True  # Default to available on error

        # Secondary check: RDAP for more accuracy (only for single checks, not bulk)
        if is_available and not skip_rdap:
            try:
                rdap_url = f"https://rdap.org/domain/{domain_name}"
                resp = requests.get(rdap_url, timeout=3, allow_redirects=True)
                if resp.status_code == 200:
                    is_available = False
            except Exception:
                pass

        return {
            "available": is_available,
            "domain": domain_name,
            "wholesale_price_inr": pricing['wholesale_price_inr'],
            "retail_price_inr": pricing['retail_price_inr'],
            "currency": "INR",
            "tld": tld,
        }

    def check_domain(self, domain_name):
        """
        Check if a domain is available using ConnectReseller API.
        Falls back to fast DNS check if API is not configured.
        """
        if not self.enabled:
            return {"error": "Domain API is not configured or disabled. Please set it up in Super Admin → Domain API."}

        tld = self._get_tld(domain_name)
        pricing = self.get_cached_price(tld)

        try:
            if self.api_key in ("demo_key", "", None):
                return self.check_domain_fast(domain_name)

            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/checkdomainavailable"
            response = requests.get(url, params={"APIKey": self.api_key, "websiteName": domain_name}, timeout=10)

            if response.status_code != 200:
                logger.error(f"ConnectReseller checkDomain returned status {response.status_code}: {response.text}")
                return self.check_domain_fast(domain_name)

            data = response.json()
            response_msg = data.get("responseMsg", {})
            status_code = response_msg.get("statusCode", 400)
            is_available = (status_code == 200)

            return {
                "available": is_available,
                "domain": domain_name,
                "wholesale_price_inr": pricing['wholesale_price_inr'],
                "retail_price_inr": pricing['retail_price_inr'],
                "currency": "INR",
                "tld": tld,
            }
        except Exception as e:
            logger.error(f"ConnectReseller check failed: {e}")
            return self.check_domain_fast(domain_name)

    def check_bulk_fast(self, base_name, tlds=None):
        """
        Check availability of base_name across multiple TLDs using PARALLEL DNS checks.
        Uses ThreadPoolExecutor — all TLDs checked concurrently in ~1-2s total.
        Like GoDaddy: instant results, not sequential.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if tlds is None:
            from data.models import TLDPrice
            active_tlds = list(TLDPrice.objects.filter(is_active=True).values_list('tld', flat=True))
            tlds = active_tlds if active_tlds else ['.com', '.in', '.net', '.org', '.co.in', '.io']

        name_parts = base_name.split('.')
        sld = name_parts[0]

        domains = [(f"{sld}{tld}", tld) for tld in tlds]
        results = []

        # Parallel DNS checks — 10 workers, all TLDs at once
        def _check(item):
            full_domain, tld = item
            return self.check_domain_fast(full_domain, skip_rdap=True)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_check, d): d for d in domains}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass

        # Sort: user's TLD first, then by price
        if tlds:
            primary_tld = tlds[0]
            results.sort(key=lambda r: (0 if r['tld'] == primary_tld else 1, r['retail_price_inr']))

        return results

    def check_bulk(self, base_name, tlds=None):
        """Check availability across multiple TLDs (parallel)."""
        return self.check_bulk_fast(base_name, tlds)

    def register_domain(self, domain_name, user_info=None, years=1, domain_order=None):
        """
        Registers a domain name using the ConnectReseller API.
        Passes the client's actual contact details from their profile.
        
        Args:
            domain_name: The domain to register
            user_info: Optional dict with contact overrides
            years: Registration duration
            domain_order: Optional DomainOrder instance — used to pull client details
        """
        if not self.enabled:
            return {"success": False, "error": "API not configured."}

        # Build contact details from client profile
        contact = {
            "FirstName": "Admin",
            "LastName": "User",
            "Email": "admin@voidpanel.com",
            "Phone": "+91.0000000000",
            "Company": "",
            "Address": "",
            "City": "",
            "State": "",
            "Zip": "",
            "Country": "IN",
        }

        if domain_order and hasattr(domain_order, 'user'):
            user = domain_order.user
            contact["FirstName"] = user.first_name or user.username
            contact["LastName"] = user.last_name or "."
            contact["Email"] = user.email or contact["Email"]

            try:
                profile = user.customer_profile
                contact["Phone"] = f"+91.{profile.phone}" if profile.phone else contact["Phone"]
                contact["Company"] = profile.company_name or ""
                contact["Address"] = profile.address or ""
                contact["City"] = profile.city or ""
                contact["State"] = profile.state or ""
                contact["Zip"] = profile.postal_code or ""
                # Map country name to 2-letter code
                country_map = {"india": "IN", "united states": "US", "united kingdom": "GB"}
                contact["Country"] = country_map.get(profile.country.lower(), profile.country[:2].upper()) if profile.country else "IN"
            except Exception:
                pass

        if user_info and isinstance(user_info, dict):
            contact.update(user_info)

        try:
            if self.api_key in ("demo_key", "", None):
                return {"success": True, "transaction_id": "SIM-847294", "domain": domain_name, "contact": contact}

            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/domainorder"
            payload = {
                "APIKey": self.api_key,
                "Websitename": domain_name,
                "ProductType": 1,
                "Duration": years,
                "ns1": "ns1.voidpanel.com",
                "ns2": "ns2.voidpanel.com",
                # Registrant contact
                "RegistrantFirstName": contact["FirstName"],
                "RegistrantLastName": contact["LastName"],
                "RegistrantEmail": contact["Email"],
                "RegistrantPhone": contact["Phone"],
                "RegistrantCompany": contact["Company"],
                "RegistrantAddress": contact["Address"],
                "RegistrantCity": contact["City"],
                "RegistrantState": contact["State"],
                "RegistrantZip": contact["Zip"],
                "RegistrantCountry": contact["Country"],
                # Admin contact (same as registrant)
                "AdminFirstName": contact["FirstName"],
                "AdminLastName": contact["LastName"],
                "AdminEmail": contact["Email"],
                "AdminPhone": contact["Phone"],
                "AdminCompany": contact["Company"],
                "AdminAddress": contact["Address"],
                "AdminCity": contact["City"],
                "AdminState": contact["State"],
                "AdminZip": contact["Zip"],
                "AdminCountry": contact["Country"],
                # Tech contact (same as registrant)
                "TechFirstName": contact["FirstName"],
                "TechLastName": contact["LastName"],
                "TechEmail": contact["Email"],
                "TechPhone": contact["Phone"],
                "TechCompany": contact["Company"],
                "TechAddress": contact["Address"],
                "TechCity": contact["City"],
                "TechState": contact["State"],
                "TechZip": contact["Zip"],
                "TechCountry": contact["Country"],
            }
            response = requests.get(url, params=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                response_msg = data.get("responseMsg", {})
                status_code = response_msg.get("statusCode", 400)
                if status_code == 200:
                    return {"success": True, "api_response": data, "contact": contact}
                else:
                    return {"success": False, "error": response_msg.get("message", "Registration failed.")}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"ConnectReseller register failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Domain Management Methods ──────────────────────────────────────────

    def get_domain_details(self, domain_name):
        """Fetch domain details from ConnectReseller API."""
        if not self.enabled or self.api_key in ("demo_key", "", None):
            return {"success": True, "demo": True, "nameservers": ["ns1.voidpanel.com", "ns2.voidpanel.com"], "lock": True}
        try:
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/getdomaindetails"
            resp = requests.get(url, params={"APIKey": self.api_key, "websiteName": domain_name}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "data": data}
            return {"success": False, "error": f"Status {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_nameservers(self, domain_name, ns1, ns2, ns3="", ns4=""):
        """Update nameservers for a domain via ConnectReseller API."""
        if not self.enabled:
            return {"success": False, "error": "API not configured."}
        if self.api_key in ("demo_key", "", None):
            return {"success": True, "demo": True, "message": f"Nameservers updated to {ns1}, {ns2}"}
        try:
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/modifynameservers"
            params = {"APIKey": self.api_key, "websiteName": domain_name, "ns1": ns1, "ns2": ns2}
            if ns3: params["ns3"] = ns3
            if ns4: params["ns4"] = ns4
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("responseMsg", {})
                if msg.get("statusCode") == 200:
                    return {"success": True, "api_response": data}
                return {"success": False, "error": msg.get("message", "Failed to update nameservers")}
            return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_contact_info(self, domain_name, contact):
        """Update WHOIS contact details for a domain via ConnectReseller API."""
        if not self.enabled:
            return {"success": False, "error": "API not configured."}
        if self.api_key in ("demo_key", "", None):
            return {"success": True, "demo": True, "message": "Contact info updated"}
        try:
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/modifycontactdetails"
            params = {
                "APIKey": self.api_key,
                "websiteName": domain_name,
                "RegistrantFirstName": contact.get("first_name", ""),
                "RegistrantLastName": contact.get("last_name", ""),
                "RegistrantEmail": contact.get("email", ""),
                "RegistrantPhone": contact.get("phone", ""),
                "RegistrantCompany": contact.get("company", ""),
                "RegistrantAddress": contact.get("address", ""),
                "RegistrantCity": contact.get("city", ""),
                "RegistrantState": contact.get("state", ""),
                "RegistrantZip": contact.get("postal_code", ""),
                "RegistrantCountry": contact.get("country", "IN"),
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("responseMsg", {})
                if msg.get("statusCode") == 200:
                    return {"success": True, "api_response": data}
                return {"success": False, "error": msg.get("message", "Failed to update contact")}
            return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_domain_lock(self, domain_name, lock=True):
        """Enable or disable transfer lock (theft protection) on a domain."""
        if not self.enabled:
            return {"success": False, "error": "API not configured."}
        if self.api_key in ("demo_key", "", None):
            return {"success": True, "demo": True, "message": f"Domain lock {'enabled' if lock else 'disabled'}"}
        try:
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/modifytheftprotection"
            resp = requests.get(url, params={"APIKey": self.api_key, "websiteName": domain_name, "status": "true" if lock else "false"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("responseMsg", {})
                if msg.get("statusCode") == 200:
                    return {"success": True}
                return {"success": False, "error": msg.get("message", "Failed")}
            return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

