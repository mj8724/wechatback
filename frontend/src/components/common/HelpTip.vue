<template>
  <span class="relative inline-flex items-center align-middle group cursor-help text-gray-400 hover:text-emerald-600 select-none ml-1">
    <!-- 默认小圆形问号图标 -->
    <slot name="icon">
      <span class="w-3.5 h-3.5 rounded-full border border-current text-[10px] leading-none flex items-center justify-center font-bold">
        ?
      </span>
    </slot>

    <!-- 悬浮弹出的气泡框 -->
    <span
      class="absolute hidden group-hover:inline-block z-50 pointer-events-none font-normal"
      :class="placementClasses"
    >
      <span class="relative block px-2.5 py-1.5 bg-gray-900/95 text-white text-xs rounded-lg shadow-xl max-w-xs w-max whitespace-pre-line leading-relaxed text-left">
        <slot>{{ text }}</slot>
        <!-- 气泡尖角 -->
        <span
          class="absolute w-0 h-0 border-4 border-transparent"
          :class="arrowClasses"
        ></span>
      </span>
    </span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: {
    type: String,
    default: '',
  },
  placement: {
    type: String,
    default: 'top', // 'top' | 'bottom' | 'left' | 'right'
  },
})

const placementClasses = computed(() => {
  switch (props.placement) {
    case 'bottom':
      return 'top-full left-1/2 -translate-x-1/2 mt-1.5'
    case 'left':
      return 'right-full top-1/2 -translate-y-1/2 mr-1.5'
    case 'right':
      return 'left-full top-1/2 -translate-y-1/2 ml-1.5'
    case 'top':
    default:
      return 'bottom-full left-1/2 -translate-x-1/2 mb-1.5'
  }
})

const arrowClasses = computed(() => {
  switch (props.placement) {
    case 'bottom':
      return 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-900/95'
    case 'left':
      return 'left-full top-1/2 -translate-y-1/2 border-l-gray-900/95'
    case 'right':
      return 'right-full top-1/2 -translate-y-1/2 border-r-gray-900/95'
    case 'top':
    default:
      return 'top-full left-1/2 -translate-x-1/2 border-t-gray-900/95'
  }
})
</script>
