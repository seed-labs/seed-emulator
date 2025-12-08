<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref, provide} from "vue";
import BaseMap from "@/components/BaseMap/index.vue"
import SettingNumItem from "./SettingNumItem.vue"
import {ElNotification} from "element-plus"
import {MapUi, type TransitMapUiOtherConfiguration} from "./ui.ts"
import {DataSource} from "./datasource.ts"

const mapRef = ref()
const TRANSIT_NUM_KEY = 'transitNumProvide'
const transitNum = ref(0);
const transitNumMax = ref(0);
const transits = ref([])
const transitsSelected = ref([])
const onTransitNumChange = (currentValue: number) => {
  if (!mapRef.value?.mapUi) return
  try {
    mapRef.value?.mapUi.onTransitNumChange(currentValue as number)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e,
      duration: 2000
    } as any)
  }
}

const onTransitsSelectedChange = (currentValue: number) => {
  if (!mapRef.value?.mapUi) return
  try {
    mapRef.value?.mapUi.onTransitsSelectedChange(currentValue as number)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e,
      duration: 2000
    } as any)
  }
}
provide(TRANSIT_NUM_KEY, {
      transitNum,
      transitNumMax,
      transits,
      transitsSelected,
      onTransitNumChange,
      onTransitsSelectedChange,
    }
)

const transitMapUiOtherConfiguration: TransitMapUiOtherConfiguration = {
  settingControls: {
    transitNumberValue: transitNum,
    transitNumberMaxValue: transitNumMax,
    transits
  },
}
</script>

<template>
  <BaseMap
      ref="mapRef"
      :setting-num-item="SettingNumItem"
      :map-ui-class="MapUi"
      :data-source-class="DataSource"
      :other-config="transitMapUiOtherConfiguration"
  />
</template>

<style scoped lang="scss">
</style>