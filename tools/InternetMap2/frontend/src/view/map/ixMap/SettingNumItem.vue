<script setup lang="ts">
import {inject} from "vue";

const KEY = 'ixNumProvide'
const injected = inject(KEY);
if (!injected) {
  throw new Error('未能成功注入父组件提供的值');
}
const ixNum = computed({
  get: () => injected.ixNum.value,
  set: (value) => {
    injected.ixNum.value = value
  }
})
const ixNumMax = computed(() => injected.ixNumMax.value)
const onIXNumChange = (newVal: number) => {
  injected.onIXNumChange(newVal)
}
</script>

<template>
  <el-form-item label="Num of IX" prop="number" label-width="150px">
    <el-input-number
        v-model="ixNum"
        :step="1"
        @change="onIXNumChange"
        :max="ixNumMax"
    />
  </el-form-item>
</template>

<style scoped lang="scss">

</style>