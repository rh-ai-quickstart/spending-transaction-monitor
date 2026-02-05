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
{{- $key := .pipelineKey -}}
add-{{ $key | lower | replace "_" "-" | trunc 50 }}-pipeline
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
    "minio_endpoint" $root.Values.minio.endpoint
    "minio_access_key" $root.Values.minio.accessKey
    "minio_secret_key" $root.Values.minio.secretKey
    "bucket_name" $root.Values.minio.bucketName
    "namespace" $root.Release.Namespace
    "deploy_model" $config.deployModel
    "register_model" $config.registerModel
    "model_registry_url" $root.Values.modelRegistry.url
    "model_registry_enabled" $root.Values.modelRegistry.enabled
    "serving_runtime" $runtimeName
    "create_serving_runtime" $createRuntime
    "serving_runtime_image" $runtimeImage
-}}
{{ $data | toJson }}
{{- end }}
