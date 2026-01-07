<template>
  <BaseMap
      :iframe-src="iframeSrc"
      :default-font-size="fontSize"
      @update:font-size="handleFontSizeChange"
  >
    <!-- 使用具名插槽 -->
    <template #console-tabs="{
      updateActiveStep,
      updatePopVisible,
      preStep,
      cancel,
      complete,
    }">
      <ConsoleTabs
          :form="form"
          :component-config="componentConfig"
          :confirm-next="onConfirmNext"
          :font-size="fontSize"
          @update:active-step="updateActiveStep"
          @update:pop-visible="updatePopVisible"
          @pre-step="preStep"
          @cancel="cancel"
          @complete="complete"
      />
    </template>
  </BaseMap>
</template>

<script setup lang="ts">
import {type ApiResponse, reqGetIP} from "@/api/index.ts";
import BaseMap from '@/components/BaseMap/index.vue'
import ConsoleTabs from './ConsoleTabs.vue'
import type {BGPConsoleForm} from "@/types";
import {executeApiCall} from '@/hook/index.ts'
import {addContentMarker, AllLoading, contentMarker, dockerExec, getBirdConfigContent} from "@/utils/tools.ts"
import {loadConfigByGlob} from '@/utils/configLoader'
import {componentRecord} from '@/config/index.ts'

// 定义 Props 类型
interface Props {
  name?: string
}

// 接收 Props
const props = withDefaults(defineProps<Props>(), {
  name: 'bgp'
})

const componentConfig = ref<any>(null)

const loadConfig = async (path: string) => {
  try {
    componentConfig.value = await loadConfigByGlob(path)
    if (!componentConfig.value) {
      console.error('未找到配置')
    }
  } catch (err: any) {
    console.error('配置加载错误:', err)
  }
}

// 监听 name 参数变化
watch(
    () => props.name,
    async (newVal) => {
      await loadConfig(componentRecord[newVal] as string)
      if (componentConfig.value.attackEffectConfig.type === 'iframe') {
        form.targetHost = componentConfig.value.attackEffectConfig.targetHost || ''
        form.targetIPs = componentConfig.value.attackEffectConfig.targetIPs || []
      }
    },
    {immediate: true}
)

const ip = ref<string>('')
const iframeSrc = ref<string>('')

// 新增字体大小状态
const fontSize = ref(20)

const form = reactive<BGPConsoleForm>({
  name: '',
  host: '',
  port: '2375',
  targetType: '',
  targetIPs: [],
  targetHost: '',
})

watch(() => ip.value, (newIp) => {
  if (newIp) {
    form.host = newIp
  }
}, {immediate: true})
const handleFontSizeChange = (val: number) => {
  fontSize.value = val
}
const onConfirmNext = async (activeStep: number, subStepIndex: number = 0): Promise<ApiResponse<any>> => {
  let ret: ApiResponse = {ok: true, result: ''}
  const allLoading = AllLoading()
  let intervalEvent = null
  try {
    intervalEvent = window.setInterval(() => {
      allLoading.setText(`[时间:${new Date().toLocaleTimeString()}] 执行中, 请等待…`)
    }, 5000);
    const cmdKwargs = componentConfig.value.config[activeStep].text[subStepIndex].cmdKwargs
    for (const kwargs of cmdKwargs) {
      kwargs.host = form.host
      kwargs.port = form.port
      if (kwargs.containerIds === undefined) {
        kwargs.containerIds = [] as string[]
      }
      if (kwargs.containerNames === undefined) {
        kwargs.containerNames = [] as string[]
      }
      if (kwargs.action === 'append') {
        kwargs.content = addContentMarker(getBirdConfigContent(form.targetIPs), contentMarker(kwargs.filepath))
      }
      ret = await dockerExec({...kwargs}) as ApiResponse
      if (!ret.ok) {
        break
      }
    }
    if (ret.ok) {
      if (activeStep === 0) {
        iframeSrc.value = `http://${form.host}:8080/pro/map`
        // iframeSrc.value = `http://${form.host}:8080/map.html`
      } else if (activeStep === componentConfig.value.config.length - 1) {
        iframeSrc.value = ''
      }
    }
  } catch (e) {
    ret = {ok: false, result: e.message}
  } finally {
    allLoading.close()
    if (intervalEvent) {
      window.clearInterval(intervalEvent)
    }
  }
  return ret
}
const getIp = async () => {
  const res = await executeApiCall(() =>
      reqGetIP()
  )
  if (res) {
    ip.value = res.result
  }
}
onMounted(() => {
  getIp()
})
</script>

<style lang="scss">
.el-loading-spinner {
  font-size: 30px;

  .el-loading-text {
    font-size: 40px;
    font-weight: bold
  }
}
</style>