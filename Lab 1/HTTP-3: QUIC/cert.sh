openssl req -x509 -nodes -keyout server.key -out server.cert \
  -subj "/CN=server.netsec.lab" \
  -addext "subjectAltName=DNS:server.netsec.lab"