<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'blocks' }">
      <h1>Blocks</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row :gutter="20" class="row">
    <el-col :span="24 / Object.keys(statisticInfo).length" v-for="(value, key, i) in statisticInfo">
      <el-card>
        <el-statistic :title="value.title" :value="value.value"/>
      </el-card>
    </el-col>
  </el-row>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <el-table :data="blocksData" v-loading="loading" max-height="500">
          <el-table-column prop="number" label="Number" width="240">
            <template #default="scope">
              <router-link
                  :to="{ name: 'blockInfo', params: { id: scope.row.number } }"
                  class="el-link el-link--primary">
                {{ scope.row.number }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="timestamp" label="Age" width="120">
            <template #default="scope">{{ timeTo(scope.row.timestamp) }}</template>
          </el-table-column>
          <el-table-column prop="txn" label="TxN" width="240"/>
          <el-table-column prop="reward" label="Reward"/>
        </el-table>
        <Pagination
            :pageParams="pageParams"
            :get-data="getData"
        />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import {ref, reactive, onMounted} from 'vue';
import {ElNotification} from "element-plus";
import {AllLoading} from '@/utils/tools'
import Pagination from "@/components/Pagination/index.vue"

import {
  timeTo,
  get_provider,
  get_blocks_with_transactions,
  get_blocks_total,
  get_blocks_24H,
  get_networkUtilization,
  get_blocks_by_mevBuilders,
  get_BurntFees,
} from "@/utils/ethersTool";
import {ethers} from "ethers";

const blocksData = ref([]);
const loading = ref(false);
const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const statisticInfo = reactive({
  networkUtilization: {
    title: 'Network Utilization (24H)',
    value: '',
  },
  lastSafeBlock: {
    title: 'LAST SAFE BLOCK',
    value: '',
  },
  blkByMevBuilders24H: {
    title: 'BLOCKS BY MEV BUILDERS (24H)',
    value: '',
  },
  burntFees: {
    title: 'BURNT FEES',
    value: '',
  },
})
const blocks24H = ref<ethers.providers.Block>([])
const provider = get_provider()

const getTableData = async () => {
  loading.value = true
  try {
    let {blocks} = await get_blocks_with_transactions(
        provider,
        pageParams.pageSize * (pageParams.currentPage - 1),
        pageParams.pageSize * pageParams.currentPage - 1,
        -1,
        true
    );
    if (blocks) {
      blocksData.value = blocks;
      blocksData.value.sort((a, b) => b.timestamp - a.timestamp)
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    loading.value = false
  }
}

const getStatisticInfoData = async () => {
  try {
    statisticInfo.networkUtilization.value = await get_networkUtilization(blocks24H.value)
    statisticInfo.blkByMevBuilders24H.value = await get_blocks_by_mevBuilders(blocks24H.value, pageParams.total)
    statisticInfo.burntFees.value = await get_BurntFees(blocks24H.value)
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {

  }
}

const getData = async () => {
  const allLoading = AllLoading()
  try {
    blocks24H.value = await get_blocks_24H(provider)
    pageParams.total = await get_blocks_total(provider)
    statisticInfo.lastSafeBlock.value = pageParams.total.toString()
    await getStatisticInfoData()
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    allLoading.close()
  }

  await getTableData()
}


onMounted(async () => {
  await getData()
})
</script>

<style scoped lang="scss">
.el-table {
  width: $el-table-width;
  min-height: $el-table-min-height;
  margin-bottom: $el-table-margin-bottom;
}

.row {
  padding-top: 10px
}
</style>