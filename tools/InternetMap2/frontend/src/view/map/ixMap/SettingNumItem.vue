<script setup lang="ts">
import {inject, computed} from "vue";
import type {IXProvider} from "@/types";

const KEY = 'ixNumProvide'
const injected = inject(KEY) as IXProvider;
if (!injected) {
  throw new Error('The value provided by the parent component failed to be injected successfully');
}
const ixNum = computed({
  get: () => injected.ixNum.value,
  set: (value) => {
    injected.ixNum.value = value
  }
})

const ixOptions = computed({
  get: () => injected.ixOptions.value,
  set: (value) => {
    injected.ixOptions.value = value
  }
})
const ixNumMax = computed(() => injected.ixNumMax.value)
const onIXNumChange = (newVal: number) => {
  injected.onIXNumChange(newVal)
}
const onIXBlur = () => {
  injected.onIXBlur(ixValue.value)
}
const ixValue = ref<string>([])
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
  <el-form-item label="IX" prop="name" label-width="150px">
    <el-select
        v-model="ixValue"
        multiple
        collapse-tags
        collapse-tags-tooltip
        placeholder="Select IX"
        style="width: 200px"
        @blur="onIXBlur"
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
</template>

<style scoped lang="scss">

</style>