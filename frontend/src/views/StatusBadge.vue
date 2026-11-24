<template>
  <span class="status-badge" :class="[`badge-${status}`, size ? `badge-${size}` : '']">
    <i :class="`ti ${icon}`" aria-hidden="true"></i>
    {{ $t(`status-${status}`) }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  size: { type: String, default: '' } // '' | 'lg'
})

const icon = computed(
  () =>
    ({
      pending: 'ti-clock',
      approved: 'ti-circle-check',
      needs_clarification: 'ti-message-circle'
    })[props.status] || 'ti-help-circle'
)
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: var(--border-radius-md);
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  white-space: nowrap;
}

.status-badge.badge-lg {
  font-size: 13px;
  padding: 5px 14px;
}

.badge-pending {
  background: var(--color-background-warning);
  color: var(--color-text-warning);
  border: 0.5px solid var(--color-border-warning);
}

.badge-approved {
  background: var(--color-background-success);
  color: var(--color-text-success);
  border: 0.5px solid var(--color-border-success);
}

.badge-needs_clarification {
  background: var(--color-background-info);
  color: var(--color-text-info);
  border: 0.5px solid var(--color-border-info);
}
</style>
