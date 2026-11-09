# HTTPS for the Django API

The provisional API host used in this example is `jamnex-api.cfe.mx`; replace
it with the hostname confirmed by CFE Infrastructure. Its internal DNS record
must point to the Debian server, and the APN must be routed to that server.
The certificate's Subject Alternative Name (SAN) must contain the hostname
and, when clients use it directly, `IP:10.14.64.15`.

## Django production settings

Set these values in `backend/.env` on Debian; do not commit that file:

```env
DEBUG=False
API_DOMAIN=jamnex-api.cfe.mx
API_IP=10.14.64.15
ALLOWED_HOSTS=localhost,127.0.0.1,jamnex-api.cfe.mx,10.14.64.15
CORS_ALLOWED_ORIGINS=https://jamnex-api.cfe.mx
CSRF_TRUSTED_ORIGINS=https://jamnex-api.cfe.mx,https://10.14.64.15
```

If the web frontend is hosted on another origin, add that exact HTTPS origin to
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`. The Android app uses native
HTTP APIs and does not rely on browser CORS.

When `DEBUG=False`, Django enables `SECURE_SSL_REDIRECT`,
`SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE`. It also trusts
`X-Forwarded-Proto: https`; Nginx below overwrites and supplies that header.
Bind Gunicorn to loopback so clients cannot bypass the TLS proxy:

```bash
cd ~/JamnexCFE/backend
gunicorn --bind 127.0.0.1:8000 config.wsgi:application
```

Run Gunicorn under the existing systemd service/supervisor in production rather
than keeping it attached to a shell.

## Nginx

Install Nginx and enable the site using the example
[`nginx-jamnex-api.conf.example`](./nginx-jamnex-api.conf.example). Install the
certificate chain and private server key at the paths configured there, then
validate and reload:

```bash
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Permit inbound TCP 443 from the required CFE Wi-Fi/APN networks. Keep Gunicorn
on loopback; do not expose port 8000 to client networks.

## Temporary test CA and server certificate

These commands create a private test CA and a server certificate containing
both the DNS and IP SANs. Use them only for a controlled test, not production.
The CA private key stays on Debian and must never be copied into the app or
repository.

```bash
sudo install -d -m 700 /etc/ssl/private/jamnex-test
sudo openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
  -out /etc/ssl/private/jamnex-test/ca.key
sudo openssl req -x509 -new -sha256 \
  -key /etc/ssl/private/jamnex-test/ca.key \
  -days 3650 \
  -out /etc/ssl/certs/jamnex-test-ca.crt \
  -subj "/CN=Jamnex Test Root CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
sudo openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
  -out /etc/ssl/private/jamnex-api.key
sudo openssl req -new -sha256 \
  -key /etc/ssl/private/jamnex-api.key \
  -out /etc/ssl/private/jamnex-api.csr \
  -subj "/CN=jamnex-api.cfe.mx"
sudo tee /etc/ssl/private/jamnex-api.ext >/dev/null <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:jamnex-api.cfe.mx,IP:10.14.64.15
EOF
sudo openssl x509 -req -sha256 \
  -in /etc/ssl/private/jamnex-api.csr \
  -CA /etc/ssl/certs/jamnex-test-ca.crt \
  -CAkey /etc/ssl/private/jamnex-test/ca.key \
  -CAcreateserial \
  -days 365 \
  -extfile /etc/ssl/private/jamnex-api.ext \
  -out /etc/ssl/certs/jamnex-api.crt
sudo sh -c 'cat /etc/ssl/certs/jamnex-api.crt /etc/ssl/certs/jamnex-test-ca.crt > /etc/ssl/certs/jamnex-api-fullchain.crt'
sudo chmod 600 /etc/ssl/private/jamnex-api.key /etc/ssl/private/jamnex-test/ca.key
```

Copy only the public CA certificate
`/etc/ssl/certs/jamnex-test-ca.crt` to
`mobile/android/app/src/main/res/raw/cfe_ca.crt`, replacing the repository's
test placeholder. Do not copy either `.key` file. Rebuild and install the APK
after replacing the CA certificate.

## Production CFE CA

Generate the server private key on Debian and submit only the CSR to the
authorized CFE certificate authority. Request a server-authentication
certificate whose SAN includes the confirmed API DNS name and `IP:10.14.64.15`
if direct-IP access is required. Install the issued server certificate and
intermediate chain in Nginx's `ssl_certificate` file, with its matching private
key in `ssl_certificate_key`. Obtain the public root/intermediate CA
certificate from Infra and place the required trust chain in
`mobile/android/app/src/main/res/raw/cfe_ca.crt`. Never distribute a CA or
server private key in source control or an APK.

## Verification

From a client on the permitted network:

```bash
curl --cacert /path/to/cfe-ca.crt https://jamnex-api.cfe.mx/api/
```

For the temporary test CA, use `jamnex-test-ca.crt`. In the EK430 logs,
`JamnexApiNetwork` reports cellular/Wi-Fi network availability and the
transport used for each HTTPS request:

```bash
adb logcat -s JamnexApiNetwork JamnexSyncWorker
```

Test with Wi-Fi off and mobile data on. A valid certificate does not create an
APN route: the APN must still resolve/reach the server on TCP 443.
