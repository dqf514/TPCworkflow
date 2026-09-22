<template>
  <div class="border rounded-lg p-2 bg-white">
    <canvas
      ref="canvasRef"
      class="w-full touch-none border border-dashed border-gray-300 rounded"
      :style="{ height: height + 'px' }"
    />
    <div class="flex gap-2 mt-2">
      <a-button size="small" @click="clear">{{ t('workflow.clear_sign') }}</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import SignaturePad from 'signature_pad'

const props = withDefaults(defineProps<{ height?: number; modelValue?: string }>(), {
  height: 160,
})
const emit = defineEmits<{ 'update:modelValue': [string] }>()
const { t } = useI18n()
const canvasRef = ref<HTMLCanvasElement | null>(null)
let pad: SignaturePad | null = null

function resize() {
  const canvas = canvasRef.value
  if (!canvas || !pad) return
  const ratio = Math.max(window.devicePixelRatio || 1, 1)
  const w = canvas.offsetWidth
  canvas.width = w * ratio
  canvas.height = props.height * ratio
  canvas.getContext('2d')?.scale(ratio, ratio)
  pad.clear()
}

function clear() {
  pad?.clear()
  emit('update:modelValue', '')
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  pad = new SignaturePad(canvas, { backgroundColor: 'rgb(255,255,255)' })
  pad.addEventListener('endStroke', () => {
    if (pad && !pad.isEmpty()) emit('update:modelValue', pad.toDataURL('image/png'))
  })
  resize()
  window.addEventListener('resize', resize)
})

onUnmounted(() => window.removeEventListener('resize', resize))

watch(
  () => props.modelValue,
  (v) => {
    if (!v && pad) pad.clear()
  },
)
</script>
