<script setup lang="ts">
import {inject} from "vue";

const KEY = 'transitNumProvide'
const injected = inject(KEY);
if (!injected) {
  throw new Error('未能成功注入父组件提供的值');
}
const transits = computed(() => injected.transits.value)
const transitNum = computed({
  get: () => injected.transitNum.value,
  set: (value) => {
    injected.transitNum.value = value
  }
})
const transitsSelected = computed({
  get: () => injected.transitsSelected.value,
  set: (value) => {
    injected.transitsSelected.value = value
  }
})
const transitNumMax = computed(() => injected.transitNumMax.value)
const onTransitNumChange = (newVal: number) => {
  injected.onTransitNumChange(newVal)
}
const onTransitsSelectedChange = (newVal: number) => {
  injected.onTransitsSelectedChange(newVal)
}
</script>

<template>
  <el-form-item label="Num of Transit" prop="number" label-width="150px">
    <el-input-number
        v-model="transitNum"
        :step="1"
        @change="onTransitNumChange"
        :max="transitNumMax"
    />
  </el-form-item>
<!--  <el-form-item label="Transits" prop="transits" label-width="150px">-->
<!--    <el-select-->
<!--        v-model="transitsSelected"-->
<!--        multiple-->
<!--        collapse-tags-->
<!--        collapse-tags-tooltip-->
<!--        placeholder="Select"-->
<!--        style="width: 240px"-->
<!--        clearable-->
<!--        filterable-->
<!--        @change="onTransitsSelectedChange"-->
<!--    >-->
<!--      <el-option-->
<!--          v-for="item in transits"-->
<!--          :key="item.value"-->
<!--          :label="item.label"-->
<!--          :value="item.value"-->
<!--      />-->
<!--    </el-select>-->
<!--  </el-form-item>-->
</template>

<style scoped lang="scss">

</style>