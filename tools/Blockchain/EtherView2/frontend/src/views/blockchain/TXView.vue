<template>
  <el-breadcrumb separator="/" style="padding-bottom: 10px">
    <el-breadcrumb-item :to="{ name: 'transactions' }">
      <h1>Transactions</h1>
    </el-breadcrumb-item>
  </el-breadcrumb>
  <el-row :gutter="20" class="row">
    <el-col :span="24 / Object.keys(statisticInfo).length" v-for="(value, key, i) in statisticInfo">
      <el-card>
        <router-link v-if="key==='pendingTx1H'"
                     :to="{ name: 'pending transactions'}"
                     class="el-link el-link--primary">
          <el-statistic :title="value.title" :value="value.value" :value-style="{color: '#409EFF'}"/>
        </router-link>
        <el-statistic v-else :title="value.title" :value="value.value"/>
      </el-card>
    </el-col>
  </el-row>
  <el-row class="row">
    <el-col :span="24">
      <el-card>
        <el-table :data="transactionsData" :max-height="styleExports.tHeight" v-loading="loading">
          <el-table-column prop="hash" label="Hash" width="360" :show-overflow-tooltip="true">
            <template #default="scope">
              <router-link
                  :to="{ name: 'txInfo', params: { id: scope.row.hash } }"
                  class="el-link el-link--primary">
                {{ scope.row.hash }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="block_number" label="blockNumber" width="120"/>
          <el-table-column prop="timestamp" label="Age" width="120">
            <template #default="scope">{{ timeTo(scope.row.timestamp) }}</template>
          </el-table-column>
          <el-table-column prop="nonce" label="Nonce" width="240" :show-overflow-tooltip="true"/>
          <el-table-column prop="gasPriceGwei" label="Gas Price" width="240" :show-overflow-tooltip="true">
            <template #default="scope">{{ scope.row.gasPriceGwei }} Gwei</template>
          </el-table-column>
          <el-table-column prop="from" label="From" width="360" :show-overflow-tooltip="true"/>
          <el-table-column prop="to" label="To" width="360" :show-overflow-tooltip="true"/>
          <el-table-column prop="value" label="Amount"/>
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
import {reqGetTxFees, reqGetTXs} from '@/api/index';
import Pagination from "@/components/Pagination/index.vue"
import {
  timeTo, countPendingTxLastHour
} from "@/utils/ethersTool";
import {AllLoading} from "@/utils/tools.ts";
import styleExports from "@/style/blockchain/index.module.scss"

const loading = ref(false);
const transactionsData = ref([]);
const pageParams = reactive({
  total: 0,
  pageSize: 50,
  currentPage: 1,
  pageSizes: [2, 5, 10, 50, 100],
})
const statisticInfo = reactive({
  TXN24H: {
    title: 'TRANSACTIONS (24H)',
    value: '',
  },
  pendingTx1H: {
    title: 'PENDING TRANSACTIONS (1H)',
    value: '',
  },
  totalTXFee24H: {
    title: 'TOTAL TRANSACTIONS FEE (24H)',
    value: '',
  },
  avgTXFee24H: {
    title: 'AVG. TRANSACTIONS FEE (24H)',
    value: '',
  },
})

const getTableData = async () => {
  loading.value = true
  try {
    let res = await reqGetTXs({
      page_size: pageParams.pageSize,
      page: pageParams.currentPage,
    });
    if (res.status) {
      transactionsData.value = res.data.txs;
      pageParams.total = res.data.total;
    } else {
      ElNotification({
        type: 'error',
        message: res.message
      })
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

const getStatisticInfo = async () => {
  const allLoading = AllLoading()
  try {
    const res = await reqGetTxFees()
    statisticInfo.pendingTx1H.value = await countPendingTxLastHour()
    if (res.status) {
      statisticInfo.TXN24H.value = res.data.total;
      statisticInfo.totalTXFee24H.value = res.data.totalFee;
      statisticInfo.avgTXFee24H.value = res.data.avgFee;
    } else {
      ElNotification({
        type: 'error',
        message: res.message
      } as any)
    }
  } catch (e) {
    ElNotification({
      type: 'error',
      message: e
    } as any)
  } finally {
    allLoading.close()
  }
}

const getData = async () => {
  await getStatisticInfo()
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