{{/*
Expand the name of the chart.
*/}}
{{- define "mesh-planner.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mesh-planner.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Render a full image reference, omitting the registry prefix when empty.
Usage: {{ include "mesh-planner.image" .Values.backend.image }}
*/}}
{{- define "mesh-planner.image" -}}
{{- if .registry -}}
{{- printf "%s/%s:%s" .registry .repository .tag -}}
{{- else -}}
{{- printf "%s:%s" .repository .tag -}}
{{- end -}}
{{- end }}

{{/*
imagePullSecrets block — renders nothing when the list is empty.
*/}}
{{- define "mesh-planner.imagePullSecrets" -}}
{{- if .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml .Values.imagePullSecrets | nindent 2 }}
{{- end }}
{{- end }}
