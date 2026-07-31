"""
management/commands/sync_domain_prices.py

Nightly management command to fetch wholesale TLD prices from ConnectReseller API,
apply the configured margin %, and upsert into the TLDPrice cache table.

Usage:
    python manage.py sync_domain_prices
    python manage.py sync_domain_prices --dry-run

Cron (runs daily at midnight):
    0 0 * * * cd /var/www/voidpanel-web && python manage.py sync_domain_prices >> /var/log/voidpanel_domain_sync.log 2>&1
"""
import logging
import requests
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from data.models import ConnectResellerConfig, TLDPrice

logger = logging.getLogger('voidpanel')

# Fallback wholesale prices (INR) if the API doesn't return pricing for a TLD
FALLBACK_PRICES_INR = {
    '.com':    Decimal('817'),
    '.in':     Decimal('499'),
    '.net':    Decimal('999'),
    '.org':    Decimal('749'),
    '.co.in':  Decimal('399'),
    '.io':     Decimal('2999'),
    '.co':     Decimal('1999'),
    '.info':   Decimal('599'),
    '.biz':    Decimal('699'),
    '.xyz':    Decimal('199'),
    '.online': Decimal('299'),
    '.store':  Decimal('399'),
    '.tech':   Decimal('349'),
    '.site':   Decimal('249'),
    '.dev':    Decimal('1099'),
    '.app':    Decimal('1099'),
    '.me':     Decimal('599'),
    '.us':     Decimal('499'),
    '.uk':     Decimal('599'),
    '.eu':     Decimal('499'),
}

# Approximate USD → INR conversion rate (updated via API in future)
USD_TO_INR = Decimal('85')


class Command(BaseCommand):
    help = 'Sync TLD prices from ConnectReseller API into the TLDPrice cache table.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Print prices without saving to DB')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        config = ConnectResellerConfig.objects.filter(is_active=True).first()

        if not config:
            self.stderr.write('No active ConnectResellerConfig found. Using fallback prices.')
            margin = Decimal('20')
            api_key = None
        else:
            margin = Decimal(config.margin_percentage)
            api_key = config.api_key
            # Mark as running
            if not dry_run:
                config.price_sync_status = 'running'
                config.save(update_fields=['price_sync_status'])

        log_lines = []
        synced_count = 0
        error_msg = None

        try:
            # Try to fetch prices from ConnectReseller API
            api_prices = {}
            if api_key and api_key not in ('demo_key', ''):
                api_prices = self._fetch_api_prices(api_key)
                if api_prices:
                    log_lines.append(f"Fetched {len(api_prices)} TLD prices from ConnectReseller API")
                else:
                    log_lines.append("API returned no prices, using fallback prices")

            # Merge: API prices take precedence, fallback fills gaps
            all_tlds = dict(FALLBACK_PRICES_INR)
            all_tlds.update(api_prices)

            for tld, wholesale_inr in all_tlds.items():
                retail_inr = wholesale_inr * (Decimal('1') + margin / Decimal('100'))
                retail_inr = retail_inr.quantize(Decimal('1'))

                if dry_run:
                    self.stdout.write(f"  {tld:10s}  wholesale=₹{wholesale_inr:<8}  retail=₹{retail_inr}")
                else:
                    TLDPrice.objects.update_or_create(
                        tld=tld,
                        defaults={
                            'wholesale_price': wholesale_inr,
                            'retail_price': retail_inr,
                            'currency': 'INR',
                        }
                    )
                synced_count += 1

            log_lines.append(f"Synced {synced_count} TLDs with {margin}% margin")
            self.stdout.write(self.style.SUCCESS(f"✓ Synced {synced_count} TLD prices (margin: {margin}%)"))

        except Exception as e:
            error_msg = str(e)
            log_lines.append(f"ERROR: {error_msg}")
            logger.error(f"sync_domain_prices failed: {e}")
            self.stderr.write(self.style.ERROR(f"✗ Sync failed: {e}"))

        # Update config with sync status
        if config and not dry_run:
            config.last_price_sync = timezone.now()
            config.price_sync_status = 'error' if error_msg else 'success'
            config.price_sync_log = '\n'.join(log_lines)
            config.save(update_fields=['last_price_sync', 'price_sync_status', 'price_sync_log'])

    def _fetch_api_prices(self, api_key):
        """
        Fetch TLD pricing from ConnectReseller API.
        Returns dict of {'.com': Decimal('817'), ...} in INR.
        """
        prices = {}
        try:
            # ConnectReseller TLD price list endpoint
            url = "https://api.connectreseller.com/ConnectReseller/ESHOP/gettldpricelist"
            resp = requests.get(url, params={"APIKey": api_key}, timeout=30)

            if resp.status_code != 200:
                logger.warning(f"ConnectReseller pricelist returned {resp.status_code}")
                return prices

            data = resp.json()
            response_data = data.get('responseData', [])

            if isinstance(response_data, list):
                for item in response_data:
                    tld_name = item.get('tldName', '')
                    reg_price = item.get('registrationPrice') or item.get('registerPrice') or item.get('price')

                    if not tld_name or reg_price is None:
                        continue

                    if not tld_name.startswith('.'):
                        tld_name = '.' + tld_name

                    try:
                        price_val = Decimal(str(reg_price))
                        # If price is small (< 100), it's probably USD — convert to INR
                        if price_val > 0:
                            if price_val < 100:
                                price_val = (price_val * USD_TO_INR).quantize(Decimal('1'))
                            prices[tld_name.lower()] = price_val
                    except Exception:
                        continue

            logger.info(f"Fetched {len(prices)} TLD prices from ConnectReseller API")

        except requests.Timeout:
            logger.warning("ConnectReseller pricelist request timed out")
        except Exception as e:
            logger.error(f"Failed to fetch TLD prices: {e}")

        return prices
