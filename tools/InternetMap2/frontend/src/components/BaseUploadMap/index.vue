<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref, onMounted, reactive, nextTick, shallowRef, type PropType, type Component, watch} from "vue";
import type {TabsPaneContext} from 'element-plus'
import {ElNotification, ElMessage, ElMessageBox} from "element-plus";
import type {Details} from '@/types'
import {allLoading} from '@/utils/tools.ts'
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
import {CLICK_CLASS} from "@/utils/map-ui.ts";
import {MapUi, type OtherConfiguration} from "@/view/map/map/ui.ts";
import {MapUi as IXMapUi, type IxMapUiOtherConfiguration} from "@/view/map/ixMap/ui.ts";
import {MapUi as TransitMapUi, type TransitMapUiOtherConfiguration} from "@/view/map/transitMap/ui.ts";
import {DataSource} from "@/view/map/map/datasource.ts";
import {DataSource as IXDataSource} from "@/view/map/ixMap/datasource.ts";
import {DataSource as TransitDataSource} from "@/view/map/transitMap/datasource.ts";
import Upload from '@/components/Upload/index.vue'


type OtherConfigOf<T> =
    T extends typeof MapUi ? OtherConfiguration :
        T extends typeof IXMapUi ? IxMapUiOtherConfiguration :
            T extends typeof TransitMapUi ? TransitMapUiOtherConfiguration :
                never;

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
  ixValue: string[]
  _ixValue: string[]
  ixNum: number
  transitValue: string[]
  _transitValue: string[]
  transitNum: number
}

const mapData = ref()
const mapUi = shallowRef<MapUi | IXMapUi | TransitMapUi>()
const serviceColors = ["black", "blue", "green", "red", "yellow", "orange"]
const inputActiveName = ref('settings')
const inputFilter = ref('')
const inputSearch = ref('')
const dialogVisible = ref(true)
const settingActiveName = ref('settings')
const classActiveName = ref('IX')
const detailsDialogVisible = ref(false)
const details = ref<Details[]>([])
const logBtnClick = ref(true)
const logAutoscrollChecked = ref(true)
const logDisableChecked = ref(false)
const ruleForm = reactive<RuleForm>({
  dragFixed: false,
  services: [],
  ixValue: [],
  _ixValue: [],
  transitValue: [],
  _transitValue: [],
  transitNum: 0,
  ixNum: 0,
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
const ixOptions = ref([])
const transitOptions = ref([])
const tooltipVisible = ref(false);
const tooltipContent = ref('');
const position = ref({
  top: 0,
  left: 0,
  bottom: 0,
  right: 0,
} as DOMRect)
const tooltipVirtualRef = ref({
  getBoundingClientRect: () => position.value,
})
const mapUiStart = ref<boolean>(false)
const arraysEqualUnordered = (arr1: string[], arr2: string[]): boolean => {
  const set1 = new Set(arr1);
  const set2 = new Set(arr2);

  if (set1.size !== set2.size) return false;
  for (const char of set1) {
    if (!set2.has(char)) {
      return false;
    }
  }

  return true;
}
const onSubmitFilter = async () => {
  if (!mapUi.value) return
  await mapUi.value?.onSubmitFilter(inputFilter.value)
  ElMessage({
    message: 'Submitted',
    type: 'success',
    duration: 1000
  })
}
const onSubmitSearch = () => {
  if (!mapUi.value) return
  mapUi.value?.onSubmitSearch(inputSearch.value)
  ElMessage({
    message: 'Submitted',
    type: 'success',
    duration: 1000
  })
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
const onIxBlur = async () => {
  if (ruleForm.ixValue.length === 0 || arraysEqualUnordered(ruleForm.ixValue, ruleForm._ixValue)) {
    return
  }
  await partStartMapUi()
  const {filteredNodes, filteredEdges} = mapUi.value?.filterGraphByIX(ruleForm.ixValue)
  mapUi.value?.render(filteredNodes, filteredEdges)
  ruleForm._ixValue = ruleForm.ixValue
}
const onIXNumChange = async () => {
  await partStartMapUi()
  const {filteredNodes, filteredEdges} = mapUi.value?.filterGraphByIXNum(ruleForm.ixNum)
  mapUi.value?.render(filteredNodes, filteredEdges)
}
const onTransitBlur = async () => {
  if (ruleForm.transitValue.length === 0 || arraysEqualUnordered(ruleForm.transitValue, ruleForm._transitValue)) {
    return
  }
  await partStartMapUi()
  const {filteredNodes, filteredEdges} = mapUi.value?.filterGraphByTransit(ruleForm.transitValue)
  mapUi.value?.render(filteredNodes, filteredEdges)
  ruleForm._transitValue = ruleForm.transitValue
}
const onTransitNumChange = async () => {
  await partStartMapUi()
  const {filteredNodes, filteredEdges} = mapUi.value?.filterGraphByTransitNum(ruleForm.transitNum)
  mapUi.value?.render(filteredNodes, filteredEdges)
}
const partStartMapUi = async () => {
  mapUi.value?.newAllLoadingInstance()
  if (!mapUiStart.value) {
    await mapUi.value?.partStart()
    mapUiStart.value = true
  }
}

watch(() => mapData.value, async (value) => {
  mapUi.value?.setVisData(value)
  const IXs = mapUi.value?.getIxs() || []
  ixOptions.value = IXs.map(ix => {
    return {
      label: ix.meta.emulatorInfo.displayname,
      value: ix.meta.emulatorInfo.name,
    }
  })
  ruleForm.ixNum = IXs.length
  const transits = mapUi.value?.getTransits() || []
  transitOptions.value = transits.map(transit => {
    return {
      label: `AS-${transit.asn} (${transit.info.length})`,
      value: `${transit.asn}`,
    }
  })
  ruleForm.transitNum = transits.length
  await ElMessageBox.confirm(
      'Do you want to display all the nodes of the Internet Map?',
      'Notice',
      {
        confirmButtonText: 'Yes',
        cancelButtonText: 'No',
        type: 'info',
        async beforeClose(action, instance, done) {
          instance.confirmButtonLoading = false;
          instance.cancelButtonLoading = false;

          try {
            if (action === 'confirm') {
              instance.confirmButtonLoading = true;
              await new Promise(resolve => setTimeout(resolve, 500));
              done();
              mapUi.value?.start();

            } else if (action === 'cancel') {
              instance.cancelButtonLoading = true;
              await new Promise(resolve => setTimeout(resolve, 500));
              done();
              ElMessage({
                type: 'info',
                message: 'Please select the options to be displayed in the "Settings -> Categories" section.',
              });
            } else {
              done();
            }
          } catch (error) {
            console.error(error);
            ElMessage.error('Operation failed. Please try again.');
          } finally {
            instance.confirmButtonLoading = false;
            instance.confirmButtonDisabled = false;
          }
        },
      }
  );
})

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
    mapUi.value = new props.mapUiClass(config, props.otherConfig);
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
    <Upload class="panel upload-panel"
            v-model:map-data="mapData"
            v-if="!mapData"
    />
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
        <el-form-item label="Classify" label-width="150px">
          <el-tabs v-model="classActiveName" type="card" class="tabs dialog-tabs">
            <el-tab-pane label="IX" name="IX">
              <el-form-item label="Name" label-width="60px">
                <el-select
                    v-model="ruleForm.ixValue"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="Select IX"
                    style="width: 200px"
                    @blur="onIxBlur"
                    filterable
                    clearable
                >
                  <el-option
                      v-for="item in ixOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="Number" label-width="60px">
                <el-input-number style="width: 200px" v-model="ruleForm.ixNum" :min="0" @change="onIXNumChange"/>
              </el-form-item>
            </el-tab-pane>
            <el-tab-pane label="Transit" name="transit">
              <el-form-item label="Name" label-width="60px">
                <el-select
                    filterable
                    clearable
                    v-model="ruleForm.transitValue"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="Select Transit"
                    style="width: 200px"
                    @blur="onTransitBlur"
                >
                  <el-option
                      v-for="item in transitOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="Number" label-width="60px">
                <el-input-number style="width: 200px" v-model="ruleForm.transitNum" :min="0"
                                 @change="onTransitNumChange"/>
              </el-form-item>
            </el-tab-pane>
          </el-tabs>
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
            <el-form-item label="Event interval (ms)" prop="interval">
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
  <el-tooltip
      v-model:visible="tooltipVisible"
      :content="tooltipContent"
      placement="bottom"
      effect="light"
      trigger="click"
      virtual-triggering
      :virtual-ref="tooltipVirtualRef"
  />
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

.panel.upload-panel {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 50vw;
}

.el-form-item .el-form-item:not(:last-child) {
  margin-bottom: 18px
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