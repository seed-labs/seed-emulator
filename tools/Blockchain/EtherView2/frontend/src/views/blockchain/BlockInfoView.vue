<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item>
      <h1>Block #{{ blockId }}</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <el-tabs v-model="activeName" class="demo-tabs" @tab-click="handleClick">
          <el-tab-pane label="Overview" name="overview">
            <el-descriptions column="1">
              <el-descriptions-item label="Block Height">kooriookami</el-descriptions-item>
              <el-descriptions-item label="Status">18100000000</el-descriptions-item>
              <el-descriptions-item label="Timestamp">Suzhou</el-descriptions-item>
              <el-descriptions-item label="Remarks">
                <el-tag size="small">School</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Transactions">
                No.1188, Wuzhong Avenue, Wuzhong District, Suzhou, Jiangsu Province
              </el-descriptions-item>
              <el-descriptions-item label="Block Reward:"> 1 ETH</el-descriptions-item>
              <el-descriptions-item label="Gas Used:"> 1 ETH</el-descriptions-item>
              <el-descriptions-item label="Gas Limit:"> 1 ETH</el-descriptions-item>
              <el-descriptions-item label="Base Fee Per Gas:"> 1 ETH</el-descriptions-item>
              <el-descriptions-item label="Burnt Fees:"> 1 ETH</el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          <el-tab-pane label="Consensus Info" name="consensusInfo">Consensus Info</el-tab-pane>
        </el-tabs>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ref, reactive, onMounted} from 'vue';
import {useRoute} from 'vue-router'
import {ElNotification} from "element-plus";
import type {TabsPaneContext} from 'element-plus'

import {
  get_block
} from "@/utils/ethersTool";

const blockData = ref([]);
const tableData = ref([]);
const loading = ref(false);
const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const route = useRoute()
const blockId = route.params.id

const getData = async () => {
  loading.value = true
  try {
    blockData.value = await get_block(blockId)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    loading.value = false
    console.log('blockData: ', blockData)
  }
}

const sliceData = () => {
  tableData.value = blocksData.value.slice(
      pageParams.pageSize * (pageParams.currentPage - 1),
      pageParams.pageSize * pageParams.currentPage,
  )
}


const activeName = ref('overview')

const handleClick = (tab: TabsPaneContext, event: Event) => {
  console.log(tab, event)
}

onMounted(async () => {
  // await getData()
})
</script>

<style scoped lang="scss">
.el-table {
  width: 100%;
  // min-height: 400px;
  margin-bottom: 20px;
}

.row {
  padding-top: 10px
}
</style>