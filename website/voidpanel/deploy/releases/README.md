# VoidPanel Releases

Place compiled release tarballs here.
Each file should be named: `voidpanel-{VERSION}.tar.gz`

## How to create a release tarball

```bash
# On your development machine, from the voidpanel-main/ directory:
VERSION=2.1.0
tar -czf voidpanel-${VERSION}.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.sqlite3' \
    --exclude='media/' \
    --exclude='.env' \
    --exclude='venv/' \
    --exclude='.venv/' \
    --transform "s,^,voidpanel-${VERSION}/," \
    .

# Upload to the server:
scp voidpanel-${VERSION}.tar.gz root@voidpanel.com:/var/www/voidpanel.com/public_html/releases/
```

## Directory Contents

| File | Description |
|------|-------------|
| `voidpanel-2.0.0.tar.gz` | v2.0.0 — Major rewrite |
| `voidpanel-2.1.0.tar.gz` | v2.1.0 — Step-by-step update system |

## Nginx serves these at:
`https://voidpanel.com/releases/voidpanel-{VERSION}.tar.gz`
