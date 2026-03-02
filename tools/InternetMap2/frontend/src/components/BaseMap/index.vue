<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref, onMounted, reactive, nextTick, shallowRef, type PropType, type Component} from "vue";
import type {TabsPaneContext} from 'element-plus'
import {ElNotification, ElMessage} from "element-plus";
import type {Details} from '@/types'
import {allLoading, getSocket} from '@/utils/tools.ts'
import {
  ArrowUpBold,
  ArrowDownBold,
  Setting,
  Document,
  VideoPause,
  VideoCamera,
  CaretLeft,
  CaretRight,
  VideoPlay,
  SwitchButton
} from '@element-plus/icons-vue'
import {CLICK_CLASS, wsDataType} from "@/utils/map-ui.ts";
import {MapUi, type OtherConfiguration} from "@/view/map/map/ui.ts";
import {MapUi as IXMapUi, type IxMapUiOtherConfiguration} from "@/view/map/ixMap/ui.ts";
import {MapUi as TransitMapUi, type TransitMapUiOtherConfiguration} from "@/view/map/transitMap/ui.ts";
import {DataSource} from "@/view/map/map/datasource.ts";
import {DataSource as IXDataSource} from "@/view/map/ixMap/datasource.ts";
import {DataSource as TransitDataSource} from "@/view/map/transitMap/datasource.ts";


// ① 为每一种 UI 类对应的配置类型建立映射
type OtherConfigOf<T> =
    T extends typeof MapUi ? OtherConfiguration :
        T extends typeof IXMapUi ? IxMapUiOtherConfiguration :
            T extends typeof TransitMapUi ? TransitMapUiOtherConfiguration :
                never;

// ② Props 使用单一泛型参数 M，M 决定 dataSource 与 otherConfig 的具体类型
interface Props<M extends typeof MapUi | typeof IXMapUi | typeof TransitMapUi> {
  settingNumItem?: PropType<Component>
  mapUiClass: M;
  dataSourceClass:
      M extends typeof MapUi ? typeof DataSource :
          M extends typeof IXMapUi ? typeof IXDataSource :
              M extends typeof TransitMapUi ? typeof TransitDataSource :
                  never;
  otherConfig: OtherConfigOf<M>;
}

const props = withDefaults(defineProps<Props<any>>(), {})

interface RuleForm {
  dragFixed: boolean
  services: string[]
}

const mapUi = shallowRef<MapUi | IXMapUi | TransitMapUi>()
const serviceColors = ["black", "blue", "green", "red", "yellow", "orange"]
const inputActiveName = ref('settings')
const inputFilter = ref('')
const inputSearch = ref('')
const dialogVisible = ref(true)
const settingActiveName = ref('settings')
const detailsDialogVisible = ref(false)
const details = ref<Details[]>([])
const logBtnClick = ref(true)
const logAutoscrollChecked = ref(true)
const logDisableChecked = ref(false)
const ruleForm = reactive<RuleForm>({
  dragFixed: false,
  services: []
})
const allService = ref<string[]>([])
const replayState = reactive({
  recording: false,
  replayPos: 0,
  replayStatus: {
    text: "Replay stopped.",
    status: 'stopped',
    disabled: false
  },
  recordButton: {
    disabled: false
  },
  replayButton: {
    disabled: false
  },
  stopButton: {
    disabled: true
  },
  forwardButton: {
    disabled: true
  },
  backwardButton: {
    disabled: true
  },
  replaySeek: {
    disabled: true,
    max: 200,
    value: 0
  },
  replayInterval: {
    disabled: false,
    value: 200
  }
})

const imgSrc = new URL('@/assets/img/worldMap.png', import.meta.url).href
const onSubmitFilter = async () => {
  if (!mapUi.value) return
  await mapUi.value?.onSubmitFilter(inputFilter.value)
  ElMessage({
    message: '已提交',
    type: 'success',
    duration: 1000
  })
}
const onSubmitSearch = () => {
  if (!mapUi.value) return
  mapUi.value?.onSubmitSearch(inputSearch.value)
}
const onTabsClick = (tab: TabsPaneContext) => {
  dialogVisible.value = tab.paneName === 'settings'
  if (!mapUi.value) return

  if (tab.paneName === 'search') {
    mapUi.value?.setFilterMode('node-search')
  } else if (tab.paneName === 'filter') {
    mapUi.value?.setFilterMode('filter')
  }
}
const onDragFixedChange = (val: boolean) => {
  if (!mapUi.value) return
  mapUi.value?.setDragFixed(val)
}
const onCheckedServicesChange = () => {
  if (!mapUi.value) return

  ruleForm.services.map((service: string) => {
    const style = {
      borderWidth: 4,
      color: {
        border: serviceColors[allService.value.findIndex(item => service === item) % serviceColors.length]
      },
    }
    mapUi.value?.updateServiceStyle(service, style)
  })
  allService.value.filter(service => !ruleForm.services.includes(service)).map(service => {
    const style = {
      borderWidth: 1,
      color: {
        border: "#000"
      },
    }
    mapUi.value?.updateServiceStyle(service, style)
  })
}
const onActionClick = (event: MouseEvent) => {
  if (!mapUi.value) return
  const target = event.target as HTMLElement;
  if (!target.classList.contains(CLICK_CLASS.PEER_ACTION_CLASS) && !target.closest(`.${CLICK_CLASS.PEER_ACTION_CLASS}`) &&
      !target.classList.contains(CLICK_CLASS.CONSOLE_CLASS) && !target.closest(`.${CLICK_CLASS.CONSOLE_CLASS}`) &&
      !target.classList.contains(CLICK_CLASS.NET_TOGGLE_CLASS) && !target.closest(`.${CLICK_CLASS.NET_TOGGLE_CLASS}`) &&
      !target.classList.contains(CLICK_CLASS.RELOAD_CLASS) && !target.closest(`.${CLICK_CLASS.RELOAD_CLASS}`)
  ) return;
  const loading = allLoading()
  try {
    if (target.classList.contains(CLICK_CLASS.PEER_ACTION_CLASS) || target.closest(`.${CLICK_CLASS.PEER_ACTION_CLASS}`)) {
      mapUi.value?.onPeerActionClick(event)
    } else if (target.classList.contains(CLICK_CLASS.CONSOLE_CLASS) || target.closest(`.${CLICK_CLASS.CONSOLE_CLASS}`)) {
      mapUi.value?.onConsoleLink(event)
    } else if (target.classList.contains(CLICK_CLASS.NET_TOGGLE_CLASS) || target.closest(`.${CLICK_CLASS.NET_TOGGLE_CLASS}`)) {
      mapUi.value?.onNetToggle(event)
    } else if (target.classList.contains(CLICK_CLASS.RELOAD_CLASS) || target.closest(`.${CLICK_CLASS.RELOAD_CLASS}`)) {
      mapUi.value?.onReloadLink(event)
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e,
      duration: 2000
    } as any)
  } finally {
    loading.close()
  }
}
const onRecordButtonClick = () => {
  if (!mapUi.value) return
  mapUi.value?.recordStartStop()
}
const onReplayButtonClick = () => {
  if (!mapUi.value) return
  mapUi.value?.replayPlayPause()
}
const onStopButtonClick = () => {
  if (!mapUi.value) return
  mapUi.value?.replayStop()
}
const onForwardButtonClick = () => {
  if (!mapUi.value) return
  mapUi.value?.replaySeek(1)
}
const onBackwardButtonClick = () => {
  if (!mapUi.value) return
  mapUi.value?.replaySeek(-1)
}
const onLogClear = () => {
  if (!mapUi.value) return
  mapUi.value?.onLogClear()
}
const onReplaySeek = () => {
  if (!mapUi.value) return
  mapUi.value?.replaySeek(replayState.replaySeek.value, true)
}
const onReplaySeekDown = () => {
  if (!mapUi.value) return
  mapUi.value?.replaySeekMousedown()
}
const onReplaySeekUp = () => {
  if (!mapUi.value) return
  mapUi.value?.replaySeekMouseup()
}
const filterClick = () => {
  if (!mapUi.value) return
  mapUi.value?.updateFilterSuggestions(inputFilter.value)
}
const searchInput = () => {
  if (!mapUi.value) return
  mapUi.value?.updateFilterSuggestions(inputSearch.value)
}

const getConsoleIframeElement = (id: string) => {
  if (!mapUi.value) return
  return mapUi.value?.getConsoleIframeElement(id)
}

const getNodeInfoByContainerName = (name: string) => {
  if (!mapUi.value) return
  return mapUi.value?.getNodeInfoByContainerName(name)
}

const packetWsSet = () => {
  const packetWs = getSocket('ws', '/packet')
  packetWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data?.type !== wsDataType.CAPTURE_PACKET) {
        return
      }
      let nodeInfo, style
      const packetNum = data.data.packetNum ?? -1
      if (packetNum === -1) {
        nodeInfo = mapUi.value?.getNodeInfoById(data.source)?.meta.emulatorInfo
        style = {
          id: data.source,
          borderWidth: 1,
          label: nodeInfo.displayname ?? `${nodeInfo.asn}/${nodeInfo.name}`,
          size: 25,
          font: {size: 14},
        }
      } else {
        style = {
          id: data.source,
          borderWidth: 4,
          label: `${packetNum}`,
          font: {size: 50},
          size: 60,
        }
      }
      mapUi.value?.updateNodeStyle(style)
    } catch (e) {
      console.log(e)
    }
  }
}

const hostWsSet = (ui: MapUi | IXMapUi | TransitMapUi) => {
  const ws = getSocket()
  ws.onmessage = (event) => {
    try {
      const {nodeId, title, cmd} = JSON.parse(event.data)
      ui.createWindow(nodeId, title, {cmd})
    } catch (e) {
      console.log(e)
    }
  }
}
onMounted(() => {
  nextTick(async () => {
    const datasource = new props.dataSourceClass();
    const config = {
      datasource,
      mapElementId: 'map',
      detailsDialogVisible,
      details,
      allService,
      filterInputValue: inputFilter,
      searchInputValue: inputSearch,
      suggestionsElementId: 'filter-suggestions',
      logPanelElementId: 'log-panel',
      logBodyElementId: 'log-body',
      logViewportElementId: 'log-viewport',
      logWrapElementId: 'log-wrap',
      logControls: {
        autoscrollCheckboxValue: logAutoscrollChecked,
        disableCheckboxValue: logDisableChecked,
        minimizeToggleElementId: 'log-panel-toggle',
      },
      replayControls: {
        recordButtonValue: replayState.recordButton,
        replayButtonValue: replayState.replayButton,
        stopButtonValue: replayState.stopButton,
        forwardButtonValue: replayState.forwardButton,
        backwardButtonValue: replayState.backwardButton,
        seekBarValue: replayState.replaySeek,
        intervalValue: replayState.replayInterval,
      },
      windowManager: {
        desktopElementId: 'console-area',
        taskbarElementId: 'taskbar'
      },
      replayStatusInfo: replayState.replayStatus,
    }
    const ui = new props.mapUiClass(config, props.otherConfig);
    await ui.start();
    // ui.setBackgroundImg(imgSrc)
    mapUi.value = ui
    hostWsSet(ui)
    packetWsSet()

    window.addEventListener('message', (e) => {
      const msg = e.data
      if (msg?.type === 'DEMO_SYSTEM_CTRL') {
        const nodeInfo = getNodeInfoByContainerName(`/${msg.name}`)
        if (!nodeInfo) {
          return
        }
        getConsoleIframeElement(nodeInfo.Id.slice(0, 12))?.contentWindow?.postMessage(
            msg,
            '*'
        )
      }
    })
  })
})
defineExpose({mapUi})
</script>

<template>
  <el-col :span="24" class="tabs-panel panel">
    <el-tabs
        v-model="inputActiveName"
        type="card"
        class="tabs input-tabs"
        @tab-click="onTabsClick"
    >
      <el-tab-pane label="Filter" name="filter">
        <el-input
            v-model="inputFilter"
            placeholder="Type a BPF expression to animate packet flows on the map..."
            class="input-with-select"
            id="input-filter"
            @click="filterClick"
        >
          <template #prepend>
            <el-button type="primary" class="submit" @click="onSubmitFilter">Submit</el-button>
          </template>
        </el-input>
      </el-tab-pane>
      <el-tab-pane label="Search" name="search">
        <el-input
            v-model="inputSearch"
            placeholder="Search networks and nodes..."
            class="input-with-select"
            id="input-search"
            @input="searchInput"
        >
          <template #prepend>
            <el-button type="primary" class="submit" @click="onSubmitSearch">Submit</el-button>
          </template>
        </el-input>
      </el-tab-pane>
      <el-tab-pane label="Settings" name="settings"/>
      <div class="suggestions" id="filter-suggestions"></div>
    </el-tabs>
  </el-col>
  <div class="map-area">
    <div class="map" id="map"></div>
    <div class="panel log-panel" id="log-panel">
      <el-button id="log-panel-toggle" :icon="logBtnClick ? ArrowUpBold : ArrowDownBold"
                 @click="logBtnClick = !logBtnClick">Log
      </el-button>
      <div class="log-wrap wrap minimized" id="log-wrap">
        <div class="log" id="log-viewport">
          <table class="log">
            <thead>
            <tr>
              <th>Time</th>
              <th>Node</th>
              <th>Log</th>
            </tr>
            </thead>
            <tbody id="log-body">
            </tbody>
          </table>
        </div>
        <el-row class="log-controls">
          <el-col :span="2">
            <el-button type="primary" id="log-clear" size="small" @click="onLogClear">clear</el-button>
          </el-col>
          <el-col :span="2">
            <el-checkbox v-model="logAutoscrollChecked" id="log-autoscroll" label="autoscroll"/>
          </el-col>
          <el-col :span="2">
            <el-checkbox v-model="logDisableChecked" id="log-disable" label="disable log"/>
          </el-col>
        </el-row>
      </div>
    </div>
    <div id="tooltip" class="tooltip" style="display:none;"></div>
  </div>
  <div class="console-area" id="console-area"></div>
  <div class="taskbar hide" id="taskbar"></div>
  <el-dialog
      v-model="dialogVisible"
      width="500"
      draggable
      :modal="false"
      :lock-scroll="false"
      @close="inputActiveName = 'filter'"
      custom-class="no-overlay-dialog"
  >
    <template #title>
      <el-icon :size="20" class="title-icon">
        <Setting/>
      </el-icon>
    </template>
    <el-tabs
        v-model="settingActiveName"
        type="card"
        class="tabs dialog-tabs"
    >
      <el-tab-pane label="Settings" name="settings">
        <el-form-item label="Drag Fixed" prop="dragFixed" label-width="150px">
          <el-switch v-model="ruleForm.dragFixed" @change="onDragFixedChange"/>
        </el-form-item>
        <component
            :is="props.settingNumItem"
        />
        <el-form-item label="Services" prop="services" v-if="allService.length" label-width="150px">
          <el-checkbox-group v-model="ruleForm.services" @change="onCheckedServicesChange">
            <el-checkbox v-for="service in allService" :label="service" :value="service" :key="service"/>
          </el-checkbox-group>
        </el-form-item>
      </el-tab-pane>
      <el-tab-pane label="Replay" name="replay">
        <div class="replay-plate-wrap wrap">
          <div class="replay-plate" id="replay-plate">
            <div id="replay-status">{{ replayState.replayStatus.text }}</div>
            <div>
              <el-tooltip placement="top">
                <template #content>start recording</template>
                <el-button id="replay-record"
                           :icon="VideoCamera"
                           :disabled="replayState.recordButton.disabled"
                           @click="onRecordButtonClick"
                />
              </el-tooltip>
              <el-tooltip placement="top">
                <template #content>start / pause replay</template>
                <el-button id="replay-replay"
                           :icon="replayState.replayStatus.status === 'playing' ? VideoPause : VideoPlay"
                           :disabled="replayState.replayButton.disabled"
                           @click="onReplayButtonClick"
                />
              </el-tooltip>
              <el-tooltip placement="top">
                <template #content>stop replay</template>
                <el-button id="replay-stop" :icon="SwitchButton" :disabled="replayState.stopButton.disabled"
                           @click="onStopButtonClick"/>
              </el-tooltip>
              <el-tooltip placement="top">
                <template #content>step backward</template>
                <el-button
                    id="replay-backward"
                    :icon="CaretLeft"
                    :disabled="replayState.backwardButton.disabled"
                    @click="onBackwardButtonClick"
                />
              </el-tooltip>
              <el-tooltip placement="top">
                <template #content>step forward</template>
                <el-button
                    id="replay-forward"
                    :icon="CaretRight"
                    :disabled="replayState.forwardButton.disabled"
                    @click="onForwardButtonClick"
                />
              </el-tooltip>
            </div>
            <div>
              <el-slider
                  v-model="replayState.replaySeek.value"
                  size="small"
                  :disabled="replayState.replaySeek.disabled"
                  @change="onReplaySeek"
                  @mousedown="onReplaySeekDown"
                  @mouseup="onReplaySeekUp"
              />
            </div>
            <el-form-item label="event interval (ms)" prop="interval">
              <el-input-number
                  id="replay-interval"
                  v-model="replayState.replayInterval.value"
                  :step="5"
                  :disabled="replayState.replayInterval.disabled"
              />
            </el-form-item>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
  <el-dialog
      v-model="detailsDialogVisible"
      width="300"
      draggable
      :modal="false"
      :lock-scroll="false"
      @click="onActionClick"
  >
    <template #title>
      <el-icon :size="20" class="title-icon">
        <Document/>
      </el-icon>
    </template>
    <el-descriptions :column="1" v-for="(detail, index) in details" :key="index" :title="detail.title">
      <template v-if="detail.title === 'BGP sessions' && !Object.keys(detail.data).length">
        <el-descriptions-item label="">No BGP peers.</el-descriptions-item>
      </template>
      <template v-else-if="detail.title === 'Actions'">
        <el-descriptions-item
            v-for="(value, _key) in detail.data"
            :key="_key"
            label="">
          <span v-html="value"/>
        </el-descriptions-item>
      </template>
      <template v-else>
        <el-descriptions-item
            v-for="(value, _key) in detail.data"
            :key="_key"
            :label="_key">
          <template v-if="Array.isArray(value)">
            {{ value[0] }}
            <span v-html="value[1]"/>
          </template>
          <template v-else>
            {{ value }}
          </template>
        </el-descriptions-item>
      </template>
    </el-descriptions>
  </el-dialog>
</template>

<style scoped lang="scss">
@use '@/style/common/window-manager.css' as *;
@use '@/style/map/map.css' as *;

.input-tabs {
  padding: 10px;

  .submit {
    background: rgb(203 216 235);
    color: blue;
  }
}

.el-slider {
  margin-left: 10px;
  width: 95%;
}
</style>

<style lang="scss">
.tabs-panel .suggestions:empty {
  display: none;
}

.tabs-panel .suggestions .suggestion {
  line-height: 2rem;
  padding-left: .5em;
  padding-right: .5em;
  cursor: pointer;
}

.tabs-panel .suggestions .suggestion .name {
  font-weight: bold;
  padding-right: .5em;
}

.tabs-panel .suggestions .suggestion .details {
  color: #666;
  font-size: .8em;
}

.tabs-panel .suggestions .suggestion.active {
  background-color: #ccc;
}

.tabs-panel .suggestions .suggestion:hover:not(.active) {
  background-color: #eee;
}

.el-dialog {
  opacity: 85%;
  position: absolute;
  left: 20px;
  top: 20px;
}
</style>