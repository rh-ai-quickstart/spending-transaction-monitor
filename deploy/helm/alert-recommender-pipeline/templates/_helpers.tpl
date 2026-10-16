{{/*
Expand the name of the chart.
*/}}
{{- define "alert-recommender-pipeline.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "alert-recommender-pipeline.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Parent-owned S4 helpers. These names avoid colliding with subchart helpers. */}}
{{- define "s4.fullname" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- if index $storage "fullnameOverride" -}}
{{- index $storage "fullnameOverride" | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := index $storage "nameOverride" | default "aws-compatible-storage" -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end }}

{{- define "s4.secretName" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- $s3 := index $storage "s3" | default dict -}}
{{- index $client "credentialsSecret" | default (index $s3 "existingSecret") | default (printf "%s-credentials" (include "s4.fullname" .)) -}}
{{- end }}

{{- define "s4.apiPort" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- $endpoint := index $client "endpoint" -}}
{{- if $endpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $port := regexFind ":[0-9]+$" $parsed.host -}}
{{- if $port -}}
{{- trimPrefix ":" $port -}}
{{- else if eq $parsed.scheme "https" -}}
443
{{- else -}}
80
{{- end -}}
{{- else -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $service := index $storage "service" | default dict -}}
{{- index $service "s3Port" | default 7480 -}}
{{- end -}}
{{- end }}

{{- define "s4.uiPort" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $service := index $storage "service" | default dict -}}
{{- index $service "port" | default 5000 -}}
{{- end }}

{{- define "s4.region" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- $s3 := index $storage "s3" | default dict -}}
{{- index $client "region" | default (index $s3 "region") | default "us-east-1" -}}
{{- end }}

{{- define "s4.endpoint" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- index $client "endpoint" | default (printf "http://%s:%s" (include "s4.fullname" .) (include "s4.apiPort" .)) -}}
{{- end }}

{{- define "s4.fqdn" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- $endpoint := index $client "endpoint" -}}
{{- if $endpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- regexReplaceAll ":[0-9]+$" $parsed.host "" -}}
{{- else -}}
{{- printf "%s.%s.svc.cluster.local" (include "s4.fullname" .) .Release.Namespace -}}
{{- end -}}
{{- end }}

{{- define "s4.endpointScheme" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- $endpoint := index $client "endpoint" -}}
{{- if $endpoint -}}
{{- $parsed := urlParse $endpoint -}}
{{- $parsed.scheme -}}
{{- else -}}
http
{{- end -}}
{{- end }}

{{- define "s4.uiEndpoint" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- index $client "uiEndpoint" | default (printf "http://%s:%s/api" (include "s4.fqdn" .) (include "s4.uiPort" .)) -}}
{{- end }}

{{- define "s4.bucketName" -}}
{{- $storage := index .Values "aws-compatible-storage" | default dict -}}
{{- $client := index $storage "client" | default dict -}}
{{- index $client "bucketName" | default "models" -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "alert-recommender-pipeline.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "alert-recommender-pipeline.labels" -}}
helm.sh/chart: {{ include "alert-recommender-pipeline.chart" . }}
{{ include "alert-recommender-pipeline.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "alert-recommender-pipeline.selectorLabels" -}}
app.kubernetes.io/name: {{ include "alert-recommender-pipeline.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "alert-recommender-pipeline.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "alert-recommender-pipeline.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get enabled pipelines from values
*/}}
{{- define "alert-recommender-pipeline.enabledPipelines" -}}
{{- $enabled := dict -}}
{{- range $key, $value := .Values.pipelines -}}
  {{- if $value.enabled -}}
    {{- $_ := set $enabled $key $value -}}
  {{- end -}}
{{- end -}}
{{ $enabled | toJson }}
{{- end }}

{{/*
Generate pipeline job name from key
*/}}
{{- define "alert-recommender-pipeline.pipelineJobName" -}}
{{- $suffix := printf "-r%d" .root.Release.Revision -}}
{{- $key := .pipelineKey | lower | replace "_" "-" -}}
{{- $base := printf "add-%s-pipeline" $key -}}
{{- printf "%s%s" ($base | trunc (int (sub 63 (len $suffix))) | trimSuffix "-") $suffix -}}
{{- end }}

{{/*
Pipeline labels
*/}}
{{- define "alert-recommender-pipeline.pipelineLabels" -}}
{{ include "alert-recommender-pipeline.labels" .root }}
alert-recommender-pipeline.ai/pipeline-key: {{ .pipelineKey }}
{{- end }}

{{/*
Get the ServingRuntime name to use
*/}}
{{- define "alert-recommender-pipeline.servingRuntimeName" -}}
{{- if .Values.serving.runtime.create -}}
{{ include "alert-recommender-pipeline.fullname" . }}-runtime
{{- else -}}
{{ .Values.serving.runtime.existingRuntime | default "alert-recommender-runtime" }}
{{- end -}}
{{- end }}

{{/*
Get the Data Science Pipelines URL
*/}}
{{- define "alert-recommender-pipeline.dsPipelinesUrl" -}}
{{- if .Values.dspa.deploy -}}
https://ds-pipeline-{{ .Values.dspa.name }}:8888
{{- else -}}
{{ .Values.dsPipelines.url }}
{{- end -}}
{{- end }}

{{/*
Prepare pipeline data for API call
*/}}
{{- define "alert-recommender-pipeline.preparePipelineData" -}}
{{- $config := .pipelineConfig -}}
{{- $root := .root -}}
{{- $runtimeName := include "alert-recommender-pipeline.servingRuntimeName" $root -}}
{{- $createRuntime := or $root.Values.serving.runtime.create $root.Values.serving.runtime.createViaPipeline -}}
{{- $runtimeImage := $root.Values.serving.runtime.image | default "docker.io/seldonio/mlserver:1.7.0-sklearn" -}}
{{- $data := dict 
    "name" $config.name
    "version" $config.version
    "data_version" $config.dataVersion
    "n_neighbors" $config.nNeighbors
    "metric" $config.metric
    "threshold" $config.threshold
    "s3_endpoint_url" (include "s4.endpoint" $root)
    "s3_region" (include "s4.region" $root)
    "bucket_name" (include "s4.bucketName" $root)
    "namespace" $root.Release.Namespace
    "deploy_model" $config.deployModel
    "register_model" $config.registerModel
    "deploy_from_registry" $config.deployFromRegistry
    "model_version_to_deploy" $config.modelVersionToDeploy
    "model_registry_url" $root.Values.modelRegistry.url
    "model_registry_enabled" $root.Values.modelRegistry.enabled
    "serving_runtime" $runtimeName
    "create_serving_runtime" $createRuntime
    "serving_runtime_image" $runtimeImage
-}}
{{ $data | toJson }}
{{- end }}
