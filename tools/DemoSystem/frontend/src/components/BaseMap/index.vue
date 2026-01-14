<template>
  <div class="main-container">
    <iframe
        v-if="iframeSrc"
        :src="iframeSrc"
        class="full-iframe"
    />
    <el-empty v-else :image-size="600" :description="alertTitle"/>
    <el-affix :offset="120" class="setting-affix">
      <el-button
          v-show="!dialogVisible"
          type="primary"
          :icon="Setting"
          circle
          class="setting-btn"
          @click="dialogVisible = true"
      />
    </el-affix>

    <!-- 使用 ResizableDialog 包裹对话框内容 -->
    <ResizableDialog
        v-model="dialogVisible"
        title="Console"
        :width="dialogWidth"
        :height="dialogHeight"
        :show-resize-hint="true"
        @resize="onDialogResize"
        @reset="onDialogReset"
        :default-font-size="props.defaultFontSize"
        :min-font-size="12"
        :max-font-size="44"
        @fontSizeChange="handleFontSizeChange"
    >
      <!-- 使用插槽 -->
      <slot
          name="console-tabs"
          :update-active-step="handleUpdateActiveStep"
          :update-pop-visible="handleUpdatePopVisible"
          :pre-step="handlePreStep"
          :cancel="handleCancel"
          :complete="handleComplete"
      >
        <div class="default-console">
          <p>请提供console-tabs插槽内容</p>
        </div>
      </slot>
    </ResizableDialog>
  </div>
</template>


<script setup lang="ts">
import {Setting} from '@element-plus/icons-vue'
import {ref, computed} from 'vue'
import {ElMessage} from 'element-plus'
import ResizableDialog from '@/components/ResizableDialog/index.vue'

interface BaseMapProps {
  defaultFontSize: number,
  iframeSrc: string,
}

interface BaseMapEmits {
  (e: 'update:active-step', value: number): void

  (e: 'update:pop-visible', value: boolean): void

  (e: 'update:font-size', value: number): void

  (e: 'pre-step'): void

  (e: 'next-button-click', value: number): void

  (e: 'cancel'): void

  (e: 'complete'): void
}

const props = defineProps<BaseMapProps>()
const emit = defineEmits<BaseMapEmits>()

const activeStep = ref(0)
const popVisible = ref(false)
const alertTitle = ref("请先选择并启动靶场")

// 对话框相关状态
const dialogVisible = ref(false)
const dialogWidth = ref('900px')
const dialogHeight = ref('700px')

const handleFontSizeChange = (fontSize: number) => {
  emit("update:font-size", fontSize)
}

// 对话框缩放处理
const onDialogResize = (size: { width: number; height: number; scale: number }) => {
  // console.log('对话框尺寸变化:', size)
  // 可以在这里保存用户偏好的尺寸
}

// 对话框重置处理
const onDialogReset = () => {
  dialogWidth.value = '900px'
  dialogHeight.value = '600px'
  ElMessage.success('对话框已重置为默认大小')
}

// 事件处理方法
const handleUpdateActiveStep = (value: number) => {
  activeStep.value = value
  emit('update:active-step', value)
}

const handleUpdatePopVisible = (value: boolean) => {
  popVisible.value = value
  emit('update:pop-visible', value)
}

const handlePreStep = () => {
  if (activeStep.value > 0) {
    activeStep.value--
  }
  emit('pre-step')
}

const handleCancel = () => {
  popVisible.value = false
  emit('cancel')
}

const handleComplete = () => {
  emit('complete')
}
</script>

<style scoped>
/* 主容器样式 */
.main-container {
  padding: 0 !important;
  margin: 0 !important;
  width: 100%;
  height: calc(100vh - var(--el-header-height) - 2 * var(--el-main-padding));
  overflow: hidden;
  position: relative;

  .el-empty {
    width: 100%;
    height: 100%;
    border: none;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
  }

  :deep(.el-empty__description p) {
    font-size: 50px;
    color: #ff4d4f;
    font-weight: 600;
    line-height: 1.5;
  }
}

/* 全屏iframe */
.full-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

/* 固定定位的图标容器 */
.setting-affix {
  position: fixed;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2000;
}

.setting-btn {
  width: 50px !important;
  height: 50px;
  font-size: 20px;
}

/* 默认控制台样式 */
.default-console {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
  font-size: 14px;
  padding: 20px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .setting-btn {
    width: 40px;
    height: 40px;
    font-size: 16px;
  }

  .setting-affix {
    left: 10px;
  }
}
</style>