<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item>
      <h1>Transaction #{{ txId }}</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <el-tabs v-model="activeName" class="demo-tabs" @tab-click="handleClick">
          <el-tab-pane label="Overview" name="overview">
            <el-descriptions :column="1">
              <el-descriptions-item
                  v-for="(value, key, i) in txData"
                  :key="key"
                  :label="key">
                {{ value }}
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          <el-tab-pane label="Consensus Info" name="consensusInfo">Consensus Info</el-tab-pane>
        </el-tabs>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ref, onMounted} from 'vue';
import {useRoute} from 'vue-router'
import {ElNotification} from "element-plus";
import type {TabsPaneContext} from 'element-plus'

import {
  get_provider,
  get_transaction_info,
} from "@/utils/ethersTool";

const txData = ref([]);
const loading = ref(false);
const route = useRoute()
const txId = route.params.id
const provider = get_provider()
const activeName = ref('overview')

const getData = async () => {
  loading.value = true
  try {
    txData.value = await get_transaction_info(txId, provider)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    loading.value = false
    console.log('txData: ', txData)
  }
}


const handleClick = (tab: TabsPaneContext, event: Event) => {
  console.log(tab, event)
}

onMounted(async () => {
  await getData()
})
</script>

<style scoped lang="scss">
.row {
  padding-top: 10px
}
</style>