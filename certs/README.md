# Generate a new certificate

```bash
sudo openssl req -new -nodes -config resslab-hub.cnf -keyout ../secrets/certs/resslab-hub_$(date +'%Y-%m-%d').key -out resslab-hub_$(date +'%Y-%m-%d').csr
```
