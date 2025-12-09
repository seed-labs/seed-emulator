<script setup lang="ts" xmlns="http://www.w3.org/1999/html">
import BaseMap from "@/components/BaseMap/index.vue"
import {MapUi, type OtherConfiguration} from "./ui.ts"
import {DataSource} from "./datasource.ts"

const otherConfiguration: OtherConfiguration = {}
</script>

<template>
  <BaseMap
      :map-ui-class="MapUi"
      :data-source-class="DataSource"
      :other-config="otherConfiguration"
  />
</template>

<style scoped lang="scss">

</style>