<script setup lang="ts">
interface Props {
  targetIPs: string[]
  targetHost: string
}

const props = withDefaults(defineProps<Props>(), {})
const emit = defineEmits(['update:targetIPs', 'update:targetHost']);
const form = reactive({
  targetIPs: props.targetIPs,
  targetHost: props.targetHost,
})
const iframeKey = ref(0)
const options = ref<{value: string, label: string}[]>([])
const onSubmit = () => {
  emit('update:targetIPs', form.targetIPs)
  emit('update:targetHost', form.targetHost)
}

const refreshIframe = () => {
  if (form.targetIPs.length && form.targetHost) {
    iframeKey.value += 1
    ElMessage.success('效果展示刷新')
  } else {
    ElMessage.warning('请先配置目标地址和网络地址块')
  }
}

const handleChange = (selectedValues: string[]) => {
  selectedValues.forEach(newValue => {
    // 检查是否已经是 options 中的值
    const exists = options.value.some(item => item.value === newValue)

    if (!exists) {
      options.value.push({
        value: newValue,
        label: newValue,
      })
    }
  })
}

defineExpose({
  refresh: refreshIframe,
})
</script>

<template>
  <el-form v-if="!props.targetIPs.length" :model="form" label-width="auto">
    <el-form-item label="目标地址">
      <el-input v-model="form.targetHost" placeholder="请输入目标地址"/>
    </el-form-item>
    <el-form-item label="网络地址块">
      <el-select
          v-model="form.targetIPs"
          clearable
          multiple
          filterable
          allow-create
          default-first-option
          :reserve-keyword="false"
          placeholder="请选择或输入目标网络地址块 (e.g 10.153.0.0/24)"
          @change="handleChange"
      >
        <el-option
            v-for="item in options"
            :key="item.value"
            :label="item.label"
            :value="item.value"
        />
      </el-select>
    </el-form-item>
    <el-form-item>
      <div style="text-align: right; width: 100%;">
        <el-button type="primary" @click="onSubmit">提交</el-button>
      </div>
    </el-form-item>
  </el-form>
  <iframe
      v-else
      :src="form.targetHost"
      class="full-iframe"
      :key="iframeKey"
  />
</template>

<style scoped lang="scss">
.full-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>