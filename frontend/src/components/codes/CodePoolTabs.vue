<template>
  <div class="flex items-center justify-between mt-4 bg-white rounded-xl shadow p-3">
    <div class="flex items-center gap-2 overflow-x-auto">
      <button
        v-for="p in poolList"
        :key="p.id"
        @click="$emit('select-pool', p.id)"
        class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap flex items-center gap-1.5"
        :class="selectedPoolId === p.id 
          ? 'bg-emerald-600 text-white shadow-sm' 
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
      >
        <span>{{ p.name }}</span>
        <span class="text-[11px] opacity-80">(待领 {{ p.unused }})</span>
      </button>
    </div>
    <button
      @click="$emit('open-pool-modal')"
      class="ml-2 px-3 py-1.5 rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 text-xs font-bold whitespace-nowrap"
    >
      ⚙️ 管理品类 ({{ poolList.length }})
    </button>
  </div>
</template>

<script setup>
defineProps({
  poolList: {
    type: Array,
    default: () => [],
  },
  selectedPoolId: {
    type: [Number, String, null],
    default: null,
  },
})

defineEmits(['select-pool', 'open-pool-modal'])
</script>
