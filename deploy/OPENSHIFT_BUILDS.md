# OpenShift Builds Guide

This guide explains how to build container images directly in OpenShift using BuildConfigs, without needing external registry access.

## 🎯 Why Use OpenShift Builds?

**Benefits:**
- ✅ No external container registry needed
- ✅ No need to push images manually
- ✅ Builds run inside the cluster
- ✅ Automatic integration with OpenShift ImageStreams
- ✅ Perfect when you don't have quay.io access
- ✅ Great for development and testing

**When to Use:**
- Development and testing environments
- Internal/air-gapped clusters
- When you don't have registry credentials
- Building from feature branches

## 🚀 Quick Start

### Option 1: One Command (Recommended)

Build everything in OpenShift and deploy:

```bash
# Development mode (no auth)
make openshift-deploy-noauth NAMESPACE=my-test

# Production mode (Keycloak)
make openshift-deploy-keycloak NAMESPACE=my-prod
```

This single command will:
1. Create BuildConfigs and ImageStreams
2. Build all 4 images in OpenShift
3. Deploy using the built images

**Time:** ~15-20 minutes for all builds

### Option 2: Step by Step

```bash
# 1. Create BuildConfigs and ImageStreams
make openshift-create-builds NAMESPACE=my-test

# 2. Build all images (runs in parallel)
make openshift-build-all NAMESPACE=my-test

# 3. Deploy using the built images
make deploy-noauth NAMESPACE=my-test \
  REGISTRY_URL=image-registry.openshift-image-registry.svc:5000 \
  REPOSITORY=my-test
```

## 📦 What Gets Created?

### ImageStreams
OpenShift ImageStreams track your container images:
- `spending-monitor-api:latest`
- `spending-monitor-ui:latest`
- `spending-monitor-db:latest`
- `spending-monitor-ingestion:latest`

### BuildConfigs
BuildConfigs define how to build each image:
- Source: GitHub repository
- Strategy: Docker build
- Context: Root directory
- Dockerfile path: `packages/*/Containerfile`

## 🔧 Configuration

### Default Settings

By default, builds use:
- **Repository:** `https://github.com/rh-ai-quickstart/spending-transaction-monitor.git`
- **Branch:** `main`
- **Build Resources:**
  - API/UI/Ingestion: 2Gi memory, 1 CPU
  - Database: 1Gi memory, 0.5 CPU

### Custom Branch

To build from a different branch (like your feature branch):

```bash
# Set GIT_BRANCH variable
make openshift-create-builds GIT_BRANCH=feat/my-feature NAMESPACE=test

# Or edit the BuildConfig after creation
oc edit bc/spending-monitor-api -n test
# Change spec.source.git.ref to your branch
```

### Custom Repository

For a fork or different repository:

```bash
# Edit deploy/openshift-builds-template.yaml
# Change ${GIT_URI} default value
```

## 📊 Build Management

### Check Build Status

```bash
# List all builds
oc get builds -n my-namespace

# Watch a specific build
oc logs -f build/spending-monitor-api-1 -n my-namespace

# Check build config
oc get bc -n my-namespace
```

### Start Individual Builds

```bash
# Build just the API
make openshift-build-api NAMESPACE=my-test

# Build just the UI
make openshift-build-ui NAMESPACE=my-test

# Build just the DB
make openshift-build-db NAMESPACE=my-test

# Build just the Ingestion service
make openshift-build-ingestion NAMESPACE=my-test
```

### Rebuild After Code Changes

```bash
# Option 1: Start a new build (quick)
oc start-build spending-monitor-api -n my-namespace --follow

# Option 2: Use make target
make openshift-build-api NAMESPACE=my-namespace

# Option 3: Rebuild all
make openshift-build-all NAMESPACE=my-namespace
```

### View Build Logs

```bash
# Latest build logs
oc logs -f bc/spending-monitor-api -n my-namespace

# Specific build number
oc logs -f build/spending-monitor-api-2 -n my-namespace

# All builds
oc get builds -n my-namespace
oc logs build/spending-monitor-api-1 -n my-namespace
```

## 🎮 Common Workflows

### Workflow 1: Initial Deployment

```bash
# 1. Create project
oc new-project my-app

# 2. Deploy everything (builds + deploys)
make openshift-deploy-noauth NAMESPACE=my-app

# 3. Get the route
oc get route -n my-app

# 4. Test
curl https://<route>/health
```

### Workflow 2: Update After Code Changes

```bash
# 1. Push your changes to GitHub

# 2. Trigger rebuild
oc start-build spending-monitor-api -n my-app --follow

# 3. Pods will automatically restart with new image
oc get pods -n my-app -w

# 4. Verify
oc logs -f deployment/spending-monitor-api -n my-app
```

### Workflow 3: Build from Feature Branch

```bash
# 1. Update BuildConfig to use your branch
oc patch bc/spending-monitor-api -n my-app \
  -p '{"spec":{"source":{"git":{"ref":"feat/my-feature"}}}}'

# 2. Start build
oc start-build spending-monitor-api -n my-app --follow

# 3. Verify image
oc get is/spending-monitor-api -n my-app
```

### Workflow 4: Switch Between Branches

```bash
# Build from main
make openshift-create-builds GIT_BRANCH=main NAMESPACE=prod

# Build from feature branch for testing
make openshift-create-builds GIT_BRANCH=feat/new-feature NAMESPACE=test
```

## 🔍 Troubleshooting

### Build Fails with OOM

**Problem:** Build pod runs out of memory

**Solution:** Increase build resources

```bash
oc patch bc/spending-monitor-api -n my-namespace -p '{
  "spec": {
    "resources": {
      "limits": {
        "memory": "6Gi",
        "cpu": "2"
      }
    }
  }
}'
```

### Build Fails to Clone Repository

**Problem:** Cannot access GitHub

**Solution:** Check cluster network policies or use a mirror

```bash
# Check if cluster can reach GitHub
oc run test --rm -it --image=alpine -- sh
# Inside pod:
apk add git
git clone https://github.com/rh-ai-quickstart/spending-transaction-monitor.git
```

### Build Fails at Dockerfile Step

**Problem:** Error during Docker build

**Solution:** Check build logs for specific error

```bash
# Get detailed logs
oc logs -f build/spending-monitor-api-1 -n my-namespace

# Check events
oc get events -n my-namespace | grep -i build
```

### Image Not Found When Deploying

**Problem:** Deployment can't find the image

**Solution:** Verify ImageStream exists

```bash
# Check ImageStreams
oc get is -n my-namespace

# Check image tags
oc describe is/spending-monitor-api -n my-namespace

# Ensure you're using internal registry
REGISTRY_URL=image-registry.openshift-image-registry.svc:5000
REPOSITORY=my-namespace  # same as namespace
```

### Builds Take Too Long

**Problem:** Builds are slow

**Options:**
1. Increase build resources (CPU/memory)
2. Use incremental builds (if supported)
3. Build in parallel (default behavior with `make openshift-build-all`)
4. Use pre-built images from quay.io (fallback)

## 📝 Build Configuration Details

### API Service Build

```yaml
dockerStrategy:
  dockerfilePath: packages/api/Containerfile
resources:
  limits:
    memory: 4Gi
    cpu: "2"
```

**Build Time:** ~5-8 minutes  
**Image Size:** ~1.5GB

### UI Service Build

```yaml
dockerStrategy:
  dockerfilePath: packages/ui/Containerfile
  buildArgs:
    - name: VITE_BYPASS_AUTH
      value: "false"
resources:
  limits:
    memory: 4Gi
    cpu: "2"
```

**Build Time:** ~8-12 minutes (npm install is slow)  
**Image Size:** ~500MB

### Database Service Build

```yaml
dockerStrategy:
  dockerfilePath: packages/db/Containerfile
resources:
  limits:
    memory: 2Gi
    cpu: "1"
```

**Build Time:** ~3-5 minutes  
**Image Size:** ~300MB

### Ingestion Service Build

```yaml
dockerStrategy:
  dockerfilePath: packages/ingestion-service/Containerfile
resources:
  limits:
    memory: 4Gi
    cpu: "2"
```

**Build Time:** ~5-8 minutes  
**Image Size:** ~1.5GB

## 🆚 Comparison: OpenShift Builds vs External Registry

| Feature | OpenShift Builds | External Registry (quay.io) |
|---------|------------------|----------------------------|
| **Setup** | No credentials needed | Requires registry login |
| **Build Location** | Inside cluster | Local machine or CI/CD |
| **Network** | Cluster pulls from GitHub | Machine pushes to registry |
| **Speed (first time)** | 15-20 min | 10-15 min |
| **Speed (rebuild)** | 15-20 min | 5-10 min |
| **Disk Space** | Uses cluster storage | Uses local disk |
| **Best For** | Dev/test, no registry access | Production, CI/CD pipelines |

## 🎯 Best Practices

### Development
1. Use `openshift-deploy-noauth` for quick iterations
2. Keep builds in separate namespaces per developer
3. Delete old builds to save space
4. Use specific branches instead of `main`

### Production
1. Use external registry (quay.io) for production
2. Use OpenShift builds for staging/test environments
3. Tag images with versions, not just `latest`
4. Set up webhooks for automatic rebuilds

### Cleanup
```bash
# Delete old builds (keeps last 3)
oc delete builds --field-selector status=complete -n my-namespace

# Delete failed builds
oc delete builds --field-selector status=failed -n my-namespace

# Remove all build resources
oc delete bc,is --selector app=spending-monitor -n my-namespace
```

## 🚀 Advanced: Automated Builds

### Webhook Triggers

Set up GitHub webhooks to trigger builds automatically:

```bash
# Get webhook URL
oc describe bc/spending-monitor-api -n my-namespace | grep -A 3 "Webhook GitHub"

# Add webhook to GitHub repository settings
```

### Image Change Triggers

Automatically redeploy when image changes:

```yaml
# Already configured in deployment
triggers:
  - type: ImageChange
    imageChangeParams:
      automatic: true
```

## 📚 Additional Resources

- [OpenShift Build Documentation](https://docs.openshift.com/container-platform/4.12/cicd/builds/understanding-image-builds.html)
- [BuildConfig API Reference](https://docs.openshift.com/container-platform/4.12/rest_api/workloads_apis/buildconfig-build-openshift-io-v1.html)
- [ImageStream Documentation](https://docs.openshift.com/container-platform/4.12/openshift_images/image-streams-manage.html)

## 🎓 Summary

**Quick Commands:**
```bash
# Complete deployment with in-cluster builds
make openshift-deploy-noauth NAMESPACE=test

# Just create build configs
make openshift-create-builds NAMESPACE=test

# Build all images
make openshift-build-all NAMESPACE=test

# Rebuild one service
make openshift-build-api NAMESPACE=test

# Check build status
oc get builds -n test

# View logs
oc logs -f bc/spending-monitor-api -n test
```

**Key Points:**
- ✅ No external registry needed
- ✅ Builds run in-cluster
- ✅ Perfect for development
- ✅ Automatic integration with deployments
- ✅ Easy to rebuild after code changes

Now you can deploy to OpenShift even without registry access! 🎉

