<template>
  <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
    <div v-for="s in statCards" :key="s.label" class="bg-white rounded-xl shadow p-4">
      <div class="text-gray-500 text-sm">{{ s.label }}</div>
      <div class="text-3xl font-bold" :class="s.color">{{ s.value }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({}),
  },
})

const statCards = computed(() => [
  { label: '总激活码数', value: props.stats.total ?? 0, color: 'text-blue-600' },
  { label: '已领取', value: props.stats.used ?? 0, color: 'text-green-600' },
  { label: '待领取', value: props.stats.unused ?? 0, color: 'text-emerald-500' },
  { label: '已服务用户', value: props.stats.users_count ?? 0, color: 'text-purple-600' },
  { label: '已取关用户', value: props.stats.unsubscribed_count ?? 0, color: 'text-amber-600' },
])
</script>
