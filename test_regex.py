import re
with open('/Users/rohan/Downloads/voidpanel-main/nginx_conf_dump.txt', 'r') as f:
    conf = f.read()

has_cache = '# VP_NGINX_CACHE_START' in conf
print("Hash cache present (before):", has_cache)

if has_cache:
    conf_disabled = re.sub(r'\s*# VP_NGINX_CACHE_START.*?# VP_NGINX_CACHE_END', '', conf, flags=re.DOTALL)
    print("Hash cache present (after sub):", '# VP_NGINX_CACHE_START' in conf_disabled)
else:
    print("No cache block found to test removal")
