{{- /*
  _helpers.tpl: Helm 模板辅助函数
*/ -}}
{{- define "project-manager.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "project-manager.labels" -}}
app.kubernetes.io/name: project-manager
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "project-manager.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
