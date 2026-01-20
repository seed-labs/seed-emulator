<template>
  <el-dialog
      v-bind="$attrs"
      :model-value="modelValue"
      :width="computedWidth"
      :height="computedHeight"
      :custom-class="customClass"
      draggable
      :modal="false"
      :show-close="false"
      @update:model-value="$emit('update:modelValue', $event)"
  >
    <!-- 自定义标题栏 -->
    <template #header>
      <div class="resizable-dialog-header" ref="headerRef">
        <div class="header-content">
          <span>{{ props.title }}</span>
        </div>
        <div class="header-actions">
          <!-- 新增字体大小控制区域 -->
          <div class="font-size-controls">
            <el-tooltip content="缩小字体" placement="bottom">
              <el-icon
                class="font-btn"
                :class="{ 'disabled': fontSize <= props.minFontSize }"
                @click="decreaseFontSize"
              >
                <Minus />
              </el-icon>
            </el-tooltip>
            <span class="font-size-display">{{ fontSize }}px</span>
            <el-tooltip content="放大字体" placement="bottom">
              <el-icon
                class="font-btn"
                :class="{ 'disabled': fontSize >= props.maxFontSize }"
                @click="increaseFontSize"
              >
                <Plus />
              </el-icon>
            </el-tooltip>
          </div>

          <el-tooltip content="重置大小" placement="bottom">
            <el-icon class="reset-btn" @click="handleReset">
              <RefreshRight/>
            </el-icon>
          </el-tooltip>
          <el-tooltip content="关闭" placement="bottom">
            <el-icon class="close-btn" @click="handleClose">
              <Close/>
            </el-icon>
          </el-tooltip>
        </div>
      </div>
    </template>

    <!-- 内容区域 - 关键：使用flex布局确保正确 -->
    <div class="dialog-content-container" :style="{ fontSize: `${fontSize}px` }">
      <slot/>
    </div>

    <!-- 底部区域 -->
    <template #footer v-if="$slots.footer">
      <div class="resizable-dialog-footer">
        <slot name="footer"></slot>
      </div>
    </template>

    <!-- 右下角缩放区域 -->
    <div
        class="resize-corner-area"
        ref="cornerRef"
        :class="{ 'resizing': isResizing }"
        @mousedown="startResize"
        @touchstart="startResize"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import {ref, computed, watch, nextTick, onMounted, onUnmounted} from 'vue'
import {RefreshRight, Close, Minus, Plus} from '@element-plus/icons-vue'
import {useGesture} from '@vueuse/gesture'

interface Props {
  modelValue: boolean
  title: string
  width?: string
  height?: string
  minWidth?: number
  maxWidth?: number
  minHeight?: number
  maxHeight?: number
  minScale?: number
  maxScale?: number
  showClose?: boolean
  showResizeHint?: boolean
  // 新增字体大小相关属性
  defaultFontSize?: number
  minFontSize?: number
  maxFontSize?: number
  fontStep?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Base map',
  width: '1200px',
  height: '900px',
  minWidth: 400,
  maxWidth: 2800,
  minHeight: 300,
  maxHeight: 2000,
  minScale: 0.5,
  maxScale: 2,
  showClose: false,
  showResizeHint: true,
  // 字体大小默认值
  defaultFontSize: 14,
  minFontSize: 12,
  maxFontSize: 44,
  fontStep: 2
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'scale': [scale: number]
  'resize': [size: { width: number; height: number; scale: number }]
  'reset': []
  'fontSizeChange': [fontSize: number]  // 新增字体大小变化事件
}>()

// Refs
const headerRef = ref<HTMLElement>()
const cornerRef = ref<HTMLElement>()
const dialogRef = ref<HTMLElement>()

// State
const scale = ref(1)
const isResizing = ref(false)
const customClass = ref('resizable-dialog-custom')
// 新增字体大小状态
const fontSize = ref(props.defaultFontSize)

// 计算宽度
const computedWidth = computed(() => {
  if (props.width.includes('%')) {
    const percent = parseFloat(props.width) * scale.value
    return `${Math.min(95, percent)}%`
  }

  const numericWidth = parseInt(props.width)
  const scaledWidth = numericWidth * scale.value
  return `${Math.min(props.maxWidth, Math.max(props.minWidth, scaledWidth))}px`
})

// 计算高度
const computedHeight = computed(() => {
  if (props.height === 'auto') return 'auto'

  if (props.height.includes('%')) {
    const percent = parseFloat(props.height) * scale.value
    return `${Math.min(90, percent)}%`
  }

  const numericHeight = parseInt(props.height)
  const scaledHeight = numericHeight * scale.value
  return `${Math.min(props.maxHeight, Math.max(props.minHeight, scaledHeight))}px`
})

// 字体大小控制函数
const increaseFontSize = () => {
  if (fontSize.value < props.maxFontSize) {
    fontSize.value += props.fontStep
    emit('fontSizeChange', fontSize.value)
  }
}

const decreaseFontSize = () => {
  if (fontSize.value > props.minFontSize) {
    fontSize.value -= props.fontStep
    emit('fontSizeChange', fontSize.value)
  }
}

// 重置时也重置字体大小
const handleReset = () => {
  if (dialogRef.value) {
    dialogRef.value.style.width = props.width
    dialogRef.value.style.height = props.height
    dialogRef.value.style.left = ''
    dialogRef.value.style.top = ''
    scale.value = 1
  }
  // 重置字体大小
  fontSize.value = props.defaultFontSize
  emit('reset')
  emit('fontSizeChange', fontSize.value)
}

// 其他原有函数保持不变
const initDialog = async () => {
  await nextTick()
  const dialog = document.querySelector('.el-dialog') as HTMLElement
  if (dialog) {
    dialogRef.value = dialog
    setupGestures()
  }
}

const setupGestures = () => {
  if (!dialogRef.value || !cornerRef.value) return

  if (headerRef.value) {
    useGesture(
        {
          onDrag: ({offset: [dx, dy], first, memo}) => {
            if (first && dialogRef.value) {
              const rect = dialogRef.value.getBoundingClientRect()
              memo = {x: rect.left, y: rect.top}
            }

            if (dialogRef.value && memo) {
              const newX = memo.x + dx
              const newY = memo.y + dy

              const maxX = window.innerWidth - dialogRef.value.offsetWidth - 20
              const maxY = window.innerHeight - dialogRef.value.offsetHeight - 20

              dialogRef.value.style.left = `${Math.max(20, Math.min(maxX, newX))}px`
              dialogRef.value.style.top = `${Math.max(20, Math.min(maxY, newY))}px`
            }

            return memo
          }
        },
        {
          domTarget: headerRef,
          eventOptions: {passive: false},
          drag: {filterTaps: true}
        }
    )
  }
}

const startResize = (e: MouseEvent | TouchEvent) => {
  e.preventDefault()
  e.stopPropagation()

  if (!dialogRef.value) return

  isResizing.value = true

  const startX = 'clientX' in e ? e.clientX : e.touches[0].clientX
  const startY = 'clientY' in e ? e.clientY : e.touches[0].clientY
  const startWidth = dialogRef.value.offsetWidth
  const startHeight = dialogRef.value.offsetHeight

  const onMove = (moveEvent: MouseEvent | TouchEvent) => {
    if (!dialogRef.value) return

    const currentX = 'clientX' in moveEvent ? moveEvent.clientX : moveEvent.touches[0].clientX
    const currentY = 'clientY' in moveEvent ? moveEvent.clientY : moveEvent.touches[0].clientY

    const deltaX = currentX - startX
    const deltaY = currentY - startY

    const newWidth = Math.max(props.minWidth, Math.min(props.maxWidth, startWidth + deltaX))
    const newHeight = Math.max(props.minHeight, Math.min(props.maxHeight, startHeight + deltaY))

    dialogRef.value.style.width = `${newWidth}px`
    dialogRef.value.style.height = `${newHeight}px`

    emit('resize', {
      width: newWidth,
      height: newHeight,
      scale: newWidth / parseInt(props.width)
    })
  }

  const onEnd = () => {
    isResizing.value = false

    document.removeEventListener('mousemove', onMove as EventListener)
    document.removeEventListener('mouseup', onEnd)
    document.removeEventListener('touchmove', onMove as EventListener)
    document.removeEventListener('touchend', onEnd)
  }

  if ('touches' in e) {
    document.addEventListener('touchmove', onMove as EventListener, {passive: false})
    document.addEventListener('touchend', onEnd)
  } else {
    document.addEventListener('mousemove', onMove as EventListener)
    document.addEventListener('mouseup', onEnd)
  }
}

const handleClose = () => {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    nextTick(() => {
      initDialog()
    })
  }
})

onMounted(() => {
  const style = document.createElement('style')
  style.dataset.resizableDialog = 'true'
  style.innerHTML = `
    .resizable-dialog-custom.el-dialog {
      position: fixed !important;
      margin: 0 !important;
      transform-origin: top left;
      transition: width 0.15s ease, height 0.15s ease;
      min-width: ${props.minWidth}px;
      min-height: ${props.minHeight}px;
      resize: none;
      user-select: none;
      overflow: hidden !important;
      display: flex !important;
      flex-direction: column !important;
    }

    .resizable-dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: move;
      user-select: none;
      padding: 12px 16px;
      background: linear-gradient(135deg, #409eff 0%, #79bbff 100%);
      color: white;
      border-radius: 4px 4px 0 0;
      flex-shrink: 0;
      height: 24px
    }

    .header-content {
      font-size: 16px;
      font-weight: 600;
    }

    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    /* 新增字体大小控制样式 */
    .font-size-controls {
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.1);
      padding: 4px 8px;
      border-radius: 4px;
      margin-right: 8px;
    }

    .font-btn {
      cursor: pointer;
      padding: 2px;
      border-radius: 2px;
      transition: all 0.2s;
      color: white;
    }

    .font-btn:hover:not(.disabled) {
      background: rgba(255, 255, 255, 0.2);
      transform: scale(1.1);
    }

    .font-btn.disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .font-size-display {
      font-size: 12px;
      font-weight: 500;
      min-width: 36px;
      text-align: center;
      color: white;
    }

    .reset-btn,
    .close-btn {
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      transition: all 0.2s;
      color: white;
    }

    .reset-btn:hover {
      background: rgba(255, 255, 255, 0.2);
      transform: rotate(90deg);
    }

    .close-btn:hover {
      background: rgba(255, 255, 255, 0.2);
      transform: scale(1.1);
    }

    /* 关键：对话框内容容器 */
    .dialog-content-container {
      flex: 1;
      overflow: hidden;
      padding: 0;
      margin: 0;
      min-height: 800px;
      /* 字体大小会通过内联样式控制 */
    }

    /* 关键：确保el-dialog__body正确显示 */
    .resizable-dialog-custom.el-dialog .el-dialog__body {
      flex: 1;
      overflow: hidden !important;
      padding: 0 !important;
      display: flex !important;
      flex-direction: column !important;
      min-height: 0 !important; /* 关键：允许收缩 */
    }

    /* 右下角缩放区域样式 */
    .resize-corner-area {
      position: absolute;
      right: 0;
      bottom: 0;
      width: 30px;
      height: 30px;
      cursor: nwse-resize;
      z-index: 1000;
      background: linear-gradient(135deg, transparent 50%, #409eff 50%);
      opacity: 0.5;
      transition: all 0.2s;
    }

    .resize-corner-area:hover {
      opacity: 1;
      background: linear-gradient(135deg, transparent 50%, #66b1ff 50%);
      width: 35px;
      height: 35px;
    }

    .resize-corner-area.resizing {
      opacity: 1;
      background: linear-gradient(135deg, transparent 50%, #ff6b6b 50%);
    }
  `
  document.head.appendChild(style)
})

onUnmounted(() => {
  const style = document.querySelector('style[data-resizable-dialog]')
  if (style) {
    style.remove()
  }
})
</script>

<style lang="scss">
.el-overlay-dialog {
  overflow-y: hidden;
}
</style>