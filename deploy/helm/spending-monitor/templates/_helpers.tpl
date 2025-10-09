{{/*
Expand the name of the chart.
*/}}
{{- define "spending-monitor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "spending-monitor.fullname" -}}
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
{{- define "spending-monitor.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "spending-monitor.labels" -}}
helm.sh/chart: {{ include "spending-monitor.chart" . }}
{{ include "spending-monitor.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "spending-monitor.selectorLabels" -}}
app.kubernetes.io/name: {{ include "spending-monitor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "spending-monitor.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "spending-monitor.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database labels
*/}}
{{- define "spending-monitor.database.labels" -}}
{{ include "spending-monitor.labels" . }}
app.kubernetes.io/component: database
{{- end }}

{{/*
Database selector labels
*/}}
{{- define "spending-monitor.database.selectorLabels" -}}
{{ include "spending-monitor.selectorLabels" . }}
app.kubernetes.io/component: database
{{- end }}

{{/*
API labels
*/}}
{{- define "spending-monitor.api.labels" -}}
{{ include "spending-monitor.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "spending-monitor.api.selectorLabels" -}}
{{ include "spending-monitor.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
UI labels
*/}}
{{- define "spending-monitor.ui.labels" -}}
{{ include "spending-monitor.labels" . }}
app.kubernetes.io/component: ui
{{- end }}

{{/*
UI selector labels
*/}}
{{- define "spending-monitor.ui.selectorLabels" -}}
{{ include "spending-monitor.selectorLabels" . }}
app.kubernetes.io/component: ui
{{- end }}

{{/*
Image name helper
*/}}
{{- define "spending-monitor.image" -}}
{{- $registry := .Values.global.imageRegistry -}}
{{- $repository := .Values.global.imageRepository -}}
{{- $name := .name -}}
{{- $tag := .tag | default .Values.global.imageTag -}}
{{- printf "%s/%s/%s:%s" $registry $repository $name $tag -}}
{{- end }}

{{/*
UI route host helper - returns the UI route hostname for shared use
Since we can't dynamically get the UI route hostname, both routes must specify the same host
If routes.ui.host is set, use that. Otherwise, don't specify host and let OpenShift generate
but this means API route needs special handling.
*/}}
{{- define "spending-monitor.ui.route.host" -}}
{{- .Values.routes.ui.host -}}
{{- end }}

{{/*
Nginx labels
*/}}
{{- define "spending-monitor.nginx.labels" -}}
{{ include "spending-monitor.labels" . }}
app.kubernetes.io/component: nginx
{{- end }}

{{/*
Nginx selector labels
*/}}
{{- define "spending-monitor.nginx.selectorLabels" -}}
{{ include "spending-monitor.selectorLabels" . }}
app.kubernetes.io/component: nginx
{{- end }}

{{/*
Migration labels
*/}}
{{- define "spending-monitor.migration.labels" -}}
{{ include "spending-monitor.labels" . }}
app.kubernetes.io/component: migration
{{- end }}

{{/*
Migration selector labels
*/}}
{{- define "spending-monitor.migration.selectorLabels" -}}
{{ include "spending-monitor.selectorLabels" . }}
app.kubernetes.io/component: migration
{{- end }}