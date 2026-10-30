<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import BaseUploadMap from "@/components/BaseUploadMap/index.vue"
import {MapUi, type UploadMapUiOtherConfiguration} from "./ui.ts"
import {DataSource} from "./datasource.ts"

const uploadMapUiOtherConfiguration: UploadMapUiOtherConfiguration = {}
</script>

<template>
  <BaseUploadMap
      ref="mapRef"
      :map-ui-class="MapUi"
      :data-source-class="DataSource"
      :other-config="uploadMapUiOtherConfiguration"
  />
</template>

<style scoped lang="scss">
</style>