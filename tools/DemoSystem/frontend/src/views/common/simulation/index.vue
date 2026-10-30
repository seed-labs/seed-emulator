<template>
  <BaseMap
      ref="baseMapRef"
      :title="title"
      :empty-title="emptyTitle"
      :iframe-src="iframeSrc"
      :default-font-size="fontSize"
      @update:font-size="handleFontSizeChange"
  >
    <!-- 使用具名插槽 -->
    <template #console-tabs>
      <ConsoleTabs
          :key="consoleTabsKey"
          :form="form"
          :component-config="componentConfig"
          :confirm-next="onConfirmNext"
          :font-size="fontSize"
      />
    </template>
  </BaseMap>
</template>

<script setup lang="ts">
import {type ApiResponse} from "@/api";
import BaseMap from '@/components/BaseMap/index.vue'
import ConsoleTabs from './ConsoleTabs.vue'
import type {BGPConsoleForm} from "@/types";
import {AllLoading, dockerExec} from "@/utils/tools.ts"
import {loadConfigByGlob} from '@/utils/configLoader.ts'
import {componentRecord} from '@/extensions'

// 定义 Props 类型
interface Props {
  simulateName?: string
}

// 接收 Props
const props = withDefaults(defineProps<Props>(), {
  simulateName: 'bgp'
})

const consoleTabsKey = ref(0)
const componentConfig = ref<any>(null)
const baseMapRef = ref<InstanceType<typeof BaseMap> | null>(null);

const loadConfig = async (path: string) => {
  try {
    componentConfig.value = await loadConfigByGlob(path)
    if (!componentConfig.value) {
      console.error('未找到配置')
    }
    title.value = componentConfig.value.baseInfo.name
    emptyTitle.value = `欢迎来到 \`${title.value}\``
  } catch (err: any) {
    console.error('配置加载错误:', err)
  }
}

// 监听 name 参数变化
watch(
    () => props.simulateName,
    async (newVal) => {
      consoleTabsKey.value++
      const componentPath = componentRecord[newVal] || componentRecord['bgp']
      await loadConfig(componentPath as string)
      // if (componentConfig.value.attackEffectConfig.type === 'iframe') {
      //   form.targetHost = componentConfig.value.attackEffectConfig.targetHost || ''
      //   form.targetIPs = componentConfig.value.attackEffectConfig.targetIPs || []
      // }
    },
    {immediate: true}
)

const ip = ref<string>('')
const iframeSrc = ref<string>('')
const title = ref<string>('BGP 前缀劫持')
const emptyTitle = ref<string>('欢迎来到 `BGP 前缀劫持` 演示')

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
const onConfirmNext = async (...stepArgs: number[]): Promise<ApiResponse<any>> => {
  if (stepArgs.length === 0) {
    return {ok: false, result: "参数有误"}
  }

  let ret: ApiResponse = {ok: true, result: ''}
  const allLoading = AllLoading()
  let intervalEvent = null, cmdKwargs: any[]
  const activeStep = stepArgs[0] as numberd
  switch (stepArgs.length) {
    case 2:
      cmdKwargs = componentConfig.value.config[activeStep].text[stepArgs[1] as number].cmdKwargs
      break
    case 3:
      cmdKwargs = componentConfig.value.config[activeStep].text[stepArgs[1] as number].cmdGroupKwargs[stepArgs[2] as number].cmdKwargs
      break
    default:
      cmdKwargs = componentConfig.value.config[activeStep].text[stepArgs[1] as number].cmdKwargs
  }
  try {
    intervalEvent = window.setInterval(() => {
      allLoading.setText(`[时间:${new Date().toLocaleTimeString()}] 执行中, 请等待…`)
    }, 5000);
    for (const kwargs of cmdKwargs) {
      kwargs.host = form.host
      kwargs.port = form.port
      if (kwargs.containerIds === undefined) {
        kwargs.containerIds = [] as string[]
      }
      if (kwargs.containerNames === undefined) {
        kwargs.containerNames = [] as string[]
      }
      if (kwargs.cmd) {
        kwargs.cmd = kwargs.cmd.replace('$hostname', form.host)
      }
      if (kwargs.action === 'terminal_exec') {
        const iframeElement = baseMapRef.value?.internetMapRef;
        if (iframeElement) {
          kwargs.terminalIframeElement = iframeElement
        } else {
          console.warn('internetMapRef 未准备好');
        }
      }
      ret = await dockerExec({...kwargs}) as ApiResponse
      if (!ret.ok) {
        break
      }
    }
    if (ret.ok) {
      if (activeStep === 0) {
        iframeSrc.value = ''
        setTimeout(() => {
          iframeSrc.value = `http://${form.host}:8080/pro/home`
        }, 1000)
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
const getIp = () => {
  ip.value = window.location.hostname
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