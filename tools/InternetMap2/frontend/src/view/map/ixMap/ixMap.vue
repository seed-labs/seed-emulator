<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import {ref, provide} from "vue";
import BaseMap from "@/components/BaseMap/index.vue"
import SettingNumItem from "./SettingNumItem.vue"
import {ElNotification} from "element-plus"
import {MapUi, type IxMapUiOtherConfiguration} from "./ui.ts"
import {DataSource} from "./datasource.ts"

const mapRef = ref()
const IX_NUM_KEY = 'ixNumProvide'
const ixNum = ref(0);
const ixNumMax = ref(0);
const ixOptions = ref([])
const onIXNumChange = (currentValue: number) => {
  if (!mapRef.value?.mapUi) return
  try {
    mapRef.value?.mapUi.onIXNumChange(currentValue as number)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e,
      duration: 2000
    } as any)
  }
}
const onIXBlur = (currentValue: string[]) => {
  if (!mapRef.value?.mapUi) return
  try {
    mapRef.value?.mapUi.onIXBlur(currentValue)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e,
      duration: 2000
    } as any)
  }
}
provide(IX_NUM_KEY, {
      ixNum,
      ixNumMax,
      ixOptions,
      onIXNumChange,
      onIXBlur,
    }
)

const ixMapUiOtherConfiguration: IxMapUiOtherConfiguration = {
  settingControls: {
    ixNumberValue: ixNum,
    ixNumberMaxValue: ixNumMax,
    ixOptions: ixOptions,
  },
}
</script>

<template>
  <BaseMap
      ref="mapRef"
      :setting-num-item="SettingNumItem"
      :map-ui-class="MapUi"
      :data-source-class="DataSource"
      :other-config="ixMapUiOtherConfiguration"
  />
</template>

<style scoped lang="scss">
</style>