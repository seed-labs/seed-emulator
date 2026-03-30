<script setup lang="ts">
import {Refresh} from "@element-plus/icons-vue";
import {inject} from "vue";
import {ElNotification} from "element-plus";

const KEY = 'refreshProvide'
const injected = inject(KEY) as { updateRefreshKey: (value: string) => void };
if (!injected) {
  throw new Error('The value provided by the parent component failed to be injected successfully');
}

const onRefresh = () => {
  injected.updateRefreshKey(Date.now().toString())
  ElNotification({
    type: 'info',
    message: 'Refresh success'
  })
}
</script>

<template>
  <template class="refresh" @click="onRefresh">
    <el-tooltip
        class="box-item"
        effect="dark"
        content="Reload"
        placement="top"
    >
      <el-icon>
        <Refresh/>
      </el-icon>
    </el-tooltip>
  </template>
</template>

<style scoped lang="scss">
.refresh {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;

  .el-icon {
    font-size: 20px;
    color: cornflowerblue;
  }
}
</style>