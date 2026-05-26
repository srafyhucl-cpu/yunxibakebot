<script setup lang="ts">
import type { ObservabilityDetailField } from "@/types/observability";

const props = defineProps<{
  visible: boolean;
  loading: boolean;
  title: string;
  subtitle: string;
  summaryLines: string[];
  detailFields: ObservabilityDetailField[];
  errorMessage?: string;
}>();

const emit = defineEmits<{
  (event: "update:visible", value: boolean): void;
}>();
</script>

<template>
  <el-drawer
    :model-value="props.visible"
    size="520px"
    destroy-on-close
    @close="emit('update:visible', false)"
  >
    <template #header>
      <div class="observability-detail__header">
        <strong>{{ props.title }}</strong>
        <span v-if="props.subtitle">{{ props.subtitle }}</span>
      </div>
    </template>

    <div v-loading="props.loading" class="observability-detail">
      <el-alert
        v-if="props.errorMessage"
        class="observability-detail__alert"
        type="error"
        :closable="false"
        :title="props.errorMessage"
      />

      <section v-if="props.summaryLines.length" class="observability-detail__section">
        <h4>摘要</h4>
        <ul class="observability-detail__summary">
          <li v-for="line in props.summaryLines" :key="line">{{ line }}</li>
        </ul>
      </section>

      <section class="observability-detail__section">
        <h4>详情</h4>
        <div class="observability-detail__fields">
          <div
            v-for="field in props.detailFields"
            :key="field.label"
            class="observability-detail__field"
          >
            <span class="observability-detail__label">{{ field.label }}</span>
            <pre class="observability-detail__value">{{ field.value }}</pre>
          </div>
        </div>
      </section>
    </div>
  </el-drawer>
</template>

<style scoped>
.observability-detail {
  display: grid;
  gap: 16px;
}

.observability-detail__header {
  display: grid;
  gap: 6px;
}

.observability-detail__header span {
  color: var(--yx-text-muted);
  font-size: 13px;
}

.observability-detail__alert {
  margin-bottom: 4px;
}

.observability-detail__section {
  display: grid;
  gap: 10px;
}

.observability-detail__section h4 {
  margin: 0;
  font-size: 14px;
}

.observability-detail__summary {
  margin: 0;
  padding-left: 18px;
  color: var(--yx-text-muted);
  font-size: 13px;
}

.observability-detail__fields {
  display: grid;
  gap: 12px;
}

.observability-detail__field {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  background: #faf7f2;
}

.observability-detail__label {
  color: var(--yx-text-muted);
  font-size: 12px;
}

.observability-detail__value {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
}
</style>
