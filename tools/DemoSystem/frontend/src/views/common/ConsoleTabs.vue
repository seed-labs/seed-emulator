<template xmlns="http://www.w3.org/1999/html">
  <div class="console-tabs-container" :style="{ fontSize: `${fontSize}px` }">
    <el-splitter layout="vertical">
      <!-- Attack effect iframe -->
      <el-splitter-panel class="iframe-panel">
        <el-tabs v-model="activeTabName" class="box-card iframe-card">
          <!--          <el-tab-pane class="iframe-wrapper" name="attackEffect">-->
          <!--            <template #label>-->
          <!--              <span class="custom-tabs-label">-->
          <!--                效果展示-->
          <!--                <el-icon @click.stop="refreshAttackEffect"><Refresh/></el-icon>-->
          <!--              </span>-->
          <!--            </template>-->
          <!--            <Iframe-->
          <!--                ref="iframeRef"-->
          <!--                v-if="componentConfig.attackEffectConfig.type === 'iframe'"-->
          <!--                v-model:target-i-ps="form.targetIPs"-->
          <!--                v-model:target-host="form.targetHost"-->
          <!--            />-->
          <!--          </el-tab-pane>-->
          <el-tab-pane class="exec-result-tab" name="execResult">
            <template #label>
              <span class="custom-tabs-label">
                执行结果
                <el-icon @click.stop="clearStepResults"><Delete/></el-icon>
              </span>
            </template>
            <div class="config-scroll-wrapper">
              <div class="config-content">
                <div class="config-items">
                  <template v-if="stepResultsList.length">
                    <div v-for="item in stepResultsList" :key="item" class="config-item">
                      <div class="item-label">
                        <pre class="output-content">{{ item }}</pre>
                      </div>
                    </div>
                  </template>
                  <el-empty v-else :image-size="200"/>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-splitter-panel>

      <el-splitter-panel>
        <el-card class="box-card console-card">
          <template #header>
            <div class="card-header">
              <span>控制台</span>
            </div>
          </template>
          <div class="console-content-wrapper">
            <div class="steps-container">
              <div class="step-cell" v-for="(e, i) in props.componentConfig.config"
                   :key="i">
                <div class="step-header">
                  <span class="step-title">{{ `${i + 1}. ${e.headerTitle}` }}</span>
                </div>
                <div class="step-content">
                  <template v-for="(t, index1) in e.text" :key="t.shortText">
                    <el-collapse v-if="t.shortText">
                      <el-collapse-item :title="setTitle(i, index1, t.shortText)" :name="index1">
                        <div v-html="t.innerHtml"/>
                      </el-collapse-item>
                      <el-space wrap v-if="t.cmdGroupKwargs && t.cmdGroupKwargs.length">
                        <el-tooltip
                            v-for="(g, index2) in t.cmdGroupKwargs"
                            :key="g.title"
                            class="box-item"
                            effect="dark"
                            :content="g.tooltip"
                            placement="bottom-start"
                        >
                          <el-button
                              type="primary"
                              :icon="VideoPlay"
                              @click="executeStep(i, index1, index2)"
                              :loading="executingSteps[i]"
                          >
                            {{ g.title }}
                          </el-button>
                        </el-tooltip>
                      </el-space>
                      <el-button
                          v-else-if="t.cmdKwargs && t.cmdKwargs.length"
                          type="success"
                          :icon="VideoPlay"
                          @click="executeStep(i, index1)"
                          :loading="executingSteps[i]"
                      >
                        运行
                      </el-button>
                    </el-collapse>
                    <el-button
                        v-else
                        type="success"
                        :icon="VideoPlay"
                        @click="executeStep(i, index1)"
                        :loading="executingSteps[i]"
                    >
                      运行
                    </el-button>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-splitter-panel>
    </el-splitter>
  </div>
</template>

<script setup lang="ts">
import {VideoPlay, Delete} from '@element-plus/icons-vue'
// import Iframe from "./AttackEffectIframe.vue"

interface ConsoleTabsProps {
  form: any
  componentConfig: any
  fontSize?: number
  confirmNext: (...stepArgs: number[]) => Promise<boolean> | boolean
}

interface ConsoleTabsEmits {
  (e: 'update:active-step', value: number): void

  (e: 'update:pop-visible', value: boolean): void

  (e: 'pre-step'): void

  (e: 'cancel'): void

  (e: 'complete'): void
}

const props = withDefaults(defineProps<ConsoleTabsProps>(), {
  fontSize: 20  // 默认字体大小
})

const emit = defineEmits<ConsoleTabsEmits>()
// const iframeRef = ref()
const fontSize = ref(props.fontSize)
const activeTabName = ref('execResult')
const executingSteps = reactive<boolean[]>(Array(props.componentConfig.config.length).fill(false))
const stepResultsList = ref<string[]>([])

// 监听字体大小变化
watch(() => props.fontSize, (newSize) => {
  fontSize.value = newSize
})
// 执行单个步骤
// const executeStep = async (stepIndex: number, subStepIndex: number = 0) => {
const executeStep = async (...stepArgs: number[]) => {
  if (stepArgs.length === 0) {
    return
  }
  const stepIndex = stepArgs[0] as number
  executingSteps[stepIndex] = true

  try {
    const res = await props.confirmNext(...stepArgs)
    if (!res.ok) {
      throw Error(res.result)
    }
    let msg
    if (stepIndex === 0 || stepIndex === props.componentConfig.config.length - 1) {
      msg = `✅ 步骤[${stepIndex + 1}] 成功\n时间:${new Date().toLocaleTimeString()}`
    } else {
      msg = `✅ 步骤[${stepArgs.map(a => a + 1).join('-')}] 成功\n时间:${new Date().toLocaleTimeString()}`
    }
    try {
      const {succeeded} = JSON.parse(res.result)
      if (succeeded && succeeded.length && succeeded[0].output !== '') {
        msg = `${msg}\n输出:\n${succeeded[0].output}`
      }
    } catch (e) {
      if (res.result != '') {
        msg = `${msg}\n输出:\n${res.result}`
      }
    }
    stepResultsList.value.push(msg)
  } catch (error) {
    stepResultsList.value.push(`❌ 步骤[${stepArgs.map(a => a + 1).join('-')}] 失败\n时间:${new Date().toLocaleTimeString()}\n错误信息: ${error}`)
  } finally {
    executingSteps[stepIndex] = false
  }
}
const setTitle = (stepIndex: number, subStepIndex: number = 0, title: string) => {
  return `${stepIndex + 1}-${subStepIndex + 1}. ${title}`
}
const clearStepResults = () => {
  stepResultsList.value = []
}

// const refreshAttackEffect = () => {
//   if (iframeRef.value) {
//     iframeRef.value.refresh()
//   }
// }
</script>

<style scoped lang="scss">
/* 主容器 */
.console-tabs-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 16px;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
  position: absolute;
  top: calc(16px + 24px + 12px + 4px);
  left: 0;
  right: 0;
  bottom: 0;

  /* 字体大小通过内联样式控制，这里移除固定值 */
}

.custom-tabs-label .el-icon {
  vertical-align: middle;
}

.custom-tabs-label span {
  vertical-align: middle;
  margin-left: 4px;
}

/* Exec Result 标签页样式 */
:deep(.exec-result-tab) {
  height: 100%;
  overflow: hidden;

  .el-tab-pane {
    height: 100%;
    overflow: hidden;
  }
}

.config-scroll-wrapper {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
}

.config-content {
  flex: 1;
  overflow-y: auto;
}

.config-items {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: #f5f7fa;
  }
}

.item-label {
  /* 字体大小由父级控制 */
  color: #606266;
  font-weight: 500;
  width: 100%;
}

.item-value {
  /* 字体大小由父级控制 */
  color: #409eff;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background: #ecf5ff;
  padding: 4px 12px;
  border-radius: 4px;
}

/* iframe卡片 */
.iframe-card {
  height: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.iframe-panel) {
  overflow: hidden;

  .el-tabs__item {
    font-size: inherit !important;
  }
}

:deep(.iframe-card .el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.iframe-wrapper {
  flex: 1;
  overflow: hidden;
  height: 100%;
}

//.iframe-card .full-iframe {
//  width: 100%;
//  height: 100%;
//  border: none;
//}

/* Console卡片 */
.console-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.console-card .el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 控制台内容包装器 */
.console-content-wrapper {
  flex: 1;
  overflow: hidden;
  padding: 20px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 步骤容器 */
.steps-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* Step Cell 样式调整 */
.step-cell {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 16px;
  background: white;
  transition: all 0.3s ease;
}

.step-cell:last-child {
  margin-bottom: 0;
}

.step-cell.active {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
}

.step-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
  border-radius: 6px 6px 0 0;
}

.step-title {
  /* 字体大小由父级控制 */
  font-weight: 600;
  color: #303133;
  flex: 1;
}

.step-content {
  padding: 16px;
  /* 覆盖 Element Plus 组件字体大小 */
  :deep(.el-collapse) {
    .el-collapse-item__header {
      font-size: inherit !important;
      font-weight: 500;
    }

    .el-collapse-item__content {
      font-size: inherit !important;

      > div {
        font-size: inherit !important;
        line-height: 1.6;
      }
    }
  }

  :deep(.el-popover) {
    font-size: inherit !important;

    > div {
      font-size: inherit !important;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      white-space: pre;
    }
  }
}

/* 输出结果样式 */
.step-output {
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #f0f2f5;
  border-bottom: 1px solid #e0e0e0;
}

.output-header span {
  /* 字体大小由父级控制 */
  font-weight: 600;
  color: #666;
}

.output-content {
  margin: 0;
  padding: 12px 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  /* 字体大小由父级控制 */
  line-height: 1.5;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .console-tabs-container {
    padding: 12px;
    gap: 12px;
  }

  .iframe-card {
    height: 150px !important;
    min-height: 150px !important;
    max-height: 150px !important;
  }
}
</style>

<style lang="scss">
.el-splitter-bar {
  height: 20px !important;
}

/* 确保 el-tabs 正确显示 */
:deep(.el-tabs) {
  height: 100%;
  display: flex;
  flex-direction: column;

  .el-tabs__content {
    flex: 1;
    overflow: hidden;

    .el-tab-pane {
      height: 100%;
    }
  }
}

/* 代码块样式 */
.code-block {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  background: #fafafa;
  margin: 10px 0;
  padding: 10px;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #e8e8e8;
}

.code-title {
  /* 字体大小由父级控制 */
  color: #666;
  font-weight: 500;
}
</style>