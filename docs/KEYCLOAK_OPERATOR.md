# Keycloak Operator Setup Guide

⚠️ **IMPORTANT**: The Keycloak Operator is a **REQUIRED PREREQUISITE** for deploying with Keycloak authentication. The Helm chart will fail the pre-flight check if the operator is not installed.

This guide explains how to install and configure the Keycloak Operator for use with the Spending Transaction Monitor.

## 📋 Prerequisites

- OpenShift 4.10+ or Kubernetes 1.24+
- **Cluster admin permissions** (required for operator installation)
- `oc` or `kubectl` CLI installed

## ⚠️ Before You Deploy

**The Keycloak Operator MUST be installed by a cluster administrator BEFORE deploying the application with `make deploy-keycloak`.**

The Helm chart includes a pre-flight check that will **fail the deployment** if:
- Keycloak CRDs are not present
- Operator is not installed

This is intentional to ensure proper setup.

---

## 🚀 Installation Methods

### Option 1: OpenShift OperatorHub (Recommended)

The easiest way on OpenShift:

```bash
# 1. Open the OpenShift Console
# 2. Navigate to: Operators → OperatorHub
# 3. Search for "Keycloak Operator"
# 4. Click "Install"
# 5. Select:
#    - Installation mode: All namespaces
#    - Update channel: stable
#    - Approval strategy: Automatic
# 6. Click "Install"
```

Or using CLI:

```bash
# Create operator namespace
oc create namespace keycloak-operator

# Create operator subscription
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: keycloak-operator
  namespace: keycloak-operator
spec:
  channel: stable
  name: keycloak-operator
  source: community-operators
  sourceNamespace: openshift-marketplace
EOF

# Wait for operator to be ready
oc wait --for=condition=Ready pod -l app.kubernetes.io/name=keycloak-operator -n keycloak-operator --timeout=300s
```

### Option 2: Direct Installation (Kubernetes/OpenShift)

Install the operator CRDs and deployment directly:

```bash
# Install CRDs
kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.0.7/kubernetes/keycloaks.k8s.keycloak.org-v1.yml
kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.0.7/kubernetes/keycloakrealmimports.k8s.keycloak.org-v1.yml

# Install operator
kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.0.7/kubernetes/kubernetes.yml
```

---

## ✅ Verify Installation

Check that the operator is running:

```bash
# Check operator pod
oc get pods -n keycloak-operator

# Check CRDs are installed
oc get crd | grep keycloak

# Expected output:
# keycloakrealmimports.k8s.keycloak.org
# keycloaks.k8s.keycloak.org
```

---

## 🔧 Deploy Keycloak with Helm Chart

Once the operator is installed, deploy the spending monitor with Keycloak:

```bash
# Deploy to sid-test namespace with Keycloak
make deploy-keycloak NAMESPACE=sid-test
```

This will create:
1. **Keycloak CR** - Operator manages Keycloak instance
2. **KeycloakRealmImport CR** - Automatically creates realm and client
3. **OpenShift Route** - Operator exposes Keycloak via route

---

## 📊 Check Deployment Status

```bash
# Check Keycloak instance
oc get keycloak -n sid-test

# Check realm import
oc get keycloakrealmimport -n sid-test

# Check Keycloak pods
oc get pods -n sid-test | grep keycloak

# Check route (created by operator)
oc get route -n sid-test | grep keycloak
```

Expected output:
```
NAME                         READY   STATUS
spending-monitor-keycloak    true    

NAME                         READY   STATUS
spending-monitor             true    

NAME                                 READY   STATUS    RESTARTS   AGE
spending-monitor-keycloak-0          1/1     Running   0          5m

NAME                              HOST/PORT
spending-monitor-keycloak-route   https://...
```

---

## 🔑 Access Keycloak Admin Console

Get the Keycloak route and admin credentials:

```bash
# Get Keycloak route
KEYCLOAK_URL=$(oc get route spending-monitor-keycloak-route -n sid-test -o jsonpath='{.spec.host}')
echo "Keycloak URL: https://$KEYCLOAK_URL"

# Get admin credentials (default in dev mode)
echo "Admin Username: admin"
echo "Admin Password: admin"

# For production, get from secret:
oc get secret spending-monitor-keycloak-initial-admin -n sid-test -o jsonpath='{.data.username}' | base64 -d
oc get secret spending-monitor-keycloak-initial-admin -n sid-test -o jsonpath='{.data.password}' | base64 -d
```

Access the admin console:
- URL: `https://<keycloak-route>/admin`
- Login with admin credentials
- Navigate to the `spending-monitor` realm

---

## 🔄 Update Application to Use Keycloak Route

After Keycloak is deployed, update the application's Keycloak URL:

```bash
# Get the Keycloak route URL
KEYCLOAK_URL="https://$(oc get route spending-monitor-keycloak-route -n sid-test -o jsonpath='{.spec.host}')"

# Update deployment with correct URL
helm upgrade spending-monitor ./deploy/helm/spending-monitor \
  --namespace sid-test \
  --values ./deploy/helm/spending-monitor/values-prod-keycloak.yaml \
  --set secrets.KEYCLOAK_URL="$KEYCLOAK_URL" \
  --reuse-values
```

Or update `.env.production`:
```bash
KEYCLOAK_URL=https://<keycloak-route-from-above>
```

Then redeploy:
```bash
make deploy-keycloak NAMESPACE=sid-test
```

---

## 🛠️ Troubleshooting

### Operator Not Installing

```bash
# Check operator logs
oc logs -l app.kubernetes.io/name=keycloak-operator -n keycloak-operator

# Check subscription status
oc describe subscription keycloak-operator -n keycloak-operator
```

### Keycloak Instance Not Starting

```bash
# Check Keycloak CR status
oc describe keycloak spending-monitor-keycloak -n sid-test

# Check Keycloak pod logs
oc logs -f spending-monitor-keycloak-0 -n sid-test

# Common issues:
# - Insufficient resources (increase limits)
# - Database connection (check DB is running)
# - Image pull issues (check network/registry access)
```

### Realm Not Importing

```bash
# Check realm import status
oc describe keycloakrealmimport spending-monitor -n sid-test

# Check if Keycloak is ready first
oc get keycloak spending-monitor-keycloak -n sid-test -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
# Should return: True

# Force reimport by deleting and recreating
oc delete keycloakrealmimport spending-monitor -n sid-test
make deploy-keycloak NAMESPACE=sid-test
```

### Application Can't Connect to Keycloak

```bash
# Verify Keycloak service exists
oc get svc -n sid-test | grep keycloak

# Test connectivity from API pod
oc exec -it deployment/spending-monitor-api -n sid-test -- \
  curl -f http://spending-monitor-keycloak-service:8080/health

# Check DNS resolution
oc exec -it deployment/spending-monitor-api -n sid-test -- \
  nslookup spending-monitor-keycloak-service
```

---

## 🔐 Production Considerations

### 1. Use External Database

For production, configure Keycloak to use an external PostgreSQL database:

```yaml
# In Keycloak CR
spec:
  db:
    vendor: postgres
    host: postgres.example.com
    port: 5432
    database: keycloak
    usernameSecret:
      name: keycloak-db-secret
      key: username
    passwordSecret:
      name: keycloak-db-secret
      key: password
```

### 2. Configure TLS

```yaml
spec:
  http:
    tlsSecret: keycloak-tls
```

### 3. Scale Replicas

```yaml
spec:
  instances: 2  # Multiple replicas for HA
```

### 4. Resource Tuning

```yaml
spec:
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"
```

---

## 📚 Additional Resources

- [Keycloak Operator Guide](https://www.keycloak.org/guides#operator)
- [Keycloak on OpenShift](https://www.keycloak.org/getting-started/getting-started-openshift)
- [Keycloak Operator GitHub](https://github.com/keycloak/keycloak-k8s-resources)
- [Keycloak Documentation](https://www.keycloak.org/documentation)

